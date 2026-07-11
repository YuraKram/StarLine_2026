import math
from collections import deque

import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from tf2_ros import TransformBroadcaster


class TurtlebotDetector(Node):
    def __init__(self):
        super().__init__('turtlebot_detector')

        self.cloud_topic = self.param('cloud_topic', '/livox/lidar')
        self.background_path = self.param(
            'background',
            '/workspace/StarLine_2026/background_voxels.npz',
        )
        self.foreground_topic = self.param('foreground_topic', '/foreground_cloud')
        self.cluster_topic = self.param('cluster_topic', '/turtlebot_cluster')
        self.child_frame_id = self.param('child_frame_id', 'detected_turtlebot')

        self.min_range = self.param('min_range', 0.2)
        self.max_range = self.param('max_range', 3.0)
        self.background_radius = self.param('background_neighbor_radius', 1)
        self.cluster_radius = self.param('cluster_neighbor_radius', 2)
        self.min_cluster_points = self.param('min_cluster_points', 10)
        self.tracking_alpha = self.param('tracking_alpha', 0.2)
        self.publish_tf = self.param('publish_tf', True)
        self.use_current_time = self.param('use_current_time_for_output', True)

        self.background_voxels, self.voxel_size = self.load_background(
            self.background_path
        )
        self.background_offsets = self.make_offsets(
            self.background_radius,
            include_zero=True,
        )
        self.cluster_offsets = self.make_offsets(
            self.cluster_radius,
            include_zero=False,
        )

        self.last_position = None

        self.foreground_pub = self.create_publisher(
            PointCloud2,
            self.foreground_topic,
            10,
        )
        self.cluster_pub = self.create_publisher(
            PointCloud2,
            self.cluster_topic,
            10,
        )
        self.tf_broadcaster = TransformBroadcaster(self)

        self.create_subscription(PointCloud2, self.cloud_topic, self.on_cloud, 10)

        self.get_logger().info(f'cloud_topic={self.cloud_topic}')
        self.get_logger().info(f'background={self.background_path}')
        self.get_logger().info(f'voxel_size={self.voxel_size}')
        self.get_logger().info(f'background_voxels={len(self.background_voxels)}')

    def param(self, name, default):
        self.declare_parameter(name, default)
        return self.get_parameter(name).value

    @staticmethod
    def xyz(point):
        if getattr(point, 'dtype', None) is not None and point.dtype.names:
            return float(point['x']), float(point['y']), float(point['z'])

        return float(point[0]), float(point[1]), float(point[2])

    @staticmethod
    def make_offsets(radius, include_zero):
        offsets = []

        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if include_zero or dx or dy or dz:
                        offsets.append((dx, dy, dz))

        return offsets

    @staticmethod
    def load_background(path):
        data = np.load(path)
        voxel_size = float(data['voxel_size'][0])
        voxels = {tuple(map(int, voxel)) for voxel in data['voxels']}
        return voxels, voxel_size

    def stamp(self, header):
        if self.use_current_time:
            return self.get_clock().now().to_msg()

        return header.stamp

    def to_voxel(self, x, y, z):
        return (
            math.floor(x / self.voxel_size),
            math.floor(y / self.voxel_size),
            math.floor(z / self.voxel_size),
        )

    def valid_point(self, x, y, z):
        if not all(map(math.isfinite, (x, y, z))):
            return False

        distance = math.sqrt(x * x + y * y + z * z)
        return self.min_range <= distance <= self.max_range

    def is_background(self, voxel):
        vx, vy, vz = voxel

        for dx, dy, dz in self.background_offsets:
            if (vx + dx, vy + dy, vz + dz) in self.background_voxels:
                return True

        return False

    def read_foreground(self, msg):
        voxels = {}

        for point in point_cloud2.read_points(
            msg,
            field_names=('x', 'y', 'z'),
            skip_nans=True,
        ):
            x, y, z = self.xyz(point)

            if not self.valid_point(x, y, z):
                continue

            voxel = self.to_voxel(x, y, z)

            if voxel in voxels or self.is_background(voxel):
                continue

            voxels[voxel] = [x, y, z]

        return voxels

    def clusterize(self, voxel_to_point):
        unvisited = set(voxel_to_point)
        clusters = []

        while unvisited:
            start = unvisited.pop()
            queue = deque([start])
            cluster = [start]

            while queue:
                vx, vy, vz = queue.popleft()

                for dx, dy, dz in self.cluster_offsets:
                    neighbor = vx + dx, vy + dy, vz + dz

                    if neighbor not in unvisited:
                        continue

                    unvisited.remove(neighbor)
                    queue.append(neighbor)
                    cluster.append(neighbor)

            if len(cluster) >= self.min_cluster_points:
                clusters.append(cluster)

        return clusters

    def select_cluster(self, clusters, voxel_to_point):
        if not clusters:
            return None

        largest_cluster = max(clusters, key=len)

        return np.array(
            [voxel_to_point[voxel] for voxel in largest_cluster],
            dtype=np.float32,
        )

    def publish_cloud(self, publisher, header, points):
        if points is None:
            points = []
        elif isinstance(points, np.ndarray):
            points = points.tolist()

        msg = point_cloud2.create_cloud_xyz32(header, points)
        msg.header.stamp = self.stamp(header)

        publisher.publish(msg)

    def cluster_position(self, points):
        position = (points.min(axis=0) + points.max(axis=0)) / 2.0

        if self.last_position is None:
            self.last_position = position
            return position

        alpha = self.tracking_alpha
        self.last_position = alpha * position + (1.0 - alpha) * self.last_position

        return self.last_position

    def publish_transform(self, header, points):
        if points is None or len(points) < self.min_cluster_points:
            return

        position = self.cluster_position(points)
        transform = TransformStamped()

        transform.header.stamp = self.stamp(header)
        transform.header.frame_id = header.frame_id
        transform.child_frame_id = self.child_frame_id

        transform.transform.translation.x = float(position[0])
        transform.transform.translation.y = float(position[1])
        transform.transform.translation.z = float(position[2])
        transform.transform.rotation.w = 1.0

        self.tf_broadcaster.sendTransform(transform)

    def on_cloud(self, msg):
        voxel_to_point = self.read_foreground(msg)
        clusters = self.clusterize(voxel_to_point)
        cluster = self.select_cluster(clusters, voxel_to_point)

        self.publish_cloud(self.foreground_pub, msg.header, list(voxel_to_point.values()))
        self.publish_cloud(self.cluster_pub, msg.header, cluster)

        if self.publish_tf:
            self.publish_transform(msg.header, cluster)

        self.get_logger().info(
            f'foreground={len(voxel_to_point)}, '
            f'clusters={len(clusters)}, '
            f'selected={0 if cluster is None else len(cluster)}'
        )


def main(args=None):
    rclpy.init(args=args)
    node = TurtlebotDetector()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()