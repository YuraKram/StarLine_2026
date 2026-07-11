import math
import numpy as np

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2


class BackgroundBuilder(Node):
    def __init__(self):
        super().__init__('background_builder')

        self.declare_parameter('cloud_topic', '/livox/lidar')
        self.declare_parameter('output', 'background_voxels.npz')
        self.declare_parameter('voxel_size', 0.05)
        self.declare_parameter('frames', 150)

        self.cloud_topic = self.get_parameter('cloud_topic').value
        self.output = self.get_parameter('output').value
        self.voxel_size = float(self.get_parameter('voxel_size').value)
        self.target_frames = int(self.get_parameter('frames').value)

        self.frames_count = 0
        self.voxels = set()

        self.sub = self.create_subscription(
            PointCloud2,
            self.cloud_topic,
            self.cloud_callback,
            10
        )

        self.get_logger().info(f'Listening: {self.cloud_topic}')
        self.get_logger().info(f'Output: {self.output}')
        self.get_logger().info(f'Voxel size: {self.voxel_size} m')
        self.get_logger().info(f'Target frames: {self.target_frames}')

    def cloud_callback(self, msg: PointCloud2):
        self.frames_count += 1

        points = point_cloud2.read_points(
            msg,
            field_names=('x', 'y', 'z'),
            skip_nans=True
        )

        added = 0

        for p in points:
            x, y, z = float(p[0]), float(p[1]), float(p[2])

            if not math.isfinite(x) or not math.isfinite(y) or not math.isfinite(z):
                continue

            # Пока фильтры очень мягкие. Потом подберём нормально.
            dist = math.sqrt(x * x + y * y + z * z)
            if dist < 0.2 or dist > 8.0:
                continue

            ix = math.floor(x / self.voxel_size)
            iy = math.floor(y / self.voxel_size)
            iz = math.floor(z / self.voxel_size)

            self.voxels.add((ix, iy, iz))
            added += 1

        self.get_logger().info(
            f'Frame {self.frames_count}/{self.target_frames}, '
            f'points added: {added}, total voxels: {len(self.voxels)}'
        )

        if self.frames_count >= self.target_frames:
            self.save_background()
            rclpy.shutdown()

    def save_background(self):
        arr = np.array(list(self.voxels), dtype=np.int32)

        np.savez_compressed(
            self.output,
            voxels=arr,
            voxel_size=np.array([self.voxel_size], dtype=np.float32)
        )

        self.get_logger().info(f'Saved {len(self.voxels)} voxels to {self.output}')


def main(args=None):
    rclpy.init(args=args)
    node = BackgroundBuilder()
    rclpy.spin(node)


if __name__ == '__main__':
    main()