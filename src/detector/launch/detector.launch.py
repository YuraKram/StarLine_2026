from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch.actions import TimerAction, DeclareLaunchArgument


def generate_launch_description():
    pkg_dir = get_package_share_directory('detector')
    rviz_config = PathJoinSubstitution([pkg_dir, 'config', 'rviz_config.rviz'])

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    background_default_path = PathJoinSubstitution([pkg_dir, 'config', 'background_voxels.npz'])
    background_file = DeclareLaunchArgument(
        'background', 
        default_value=background_default_path,
        description='Path to background file'
    )

    detector_node = Node(
            package='detector',
            executable='detector',
            name='detector',
            parameters=[{'use_sim_time': use_sim_time,
                         'background': LaunchConfiguration('background'),}],
            output='screen'
        )

    delayed_detector = TimerAction(period=3.0, actions=[detector_node])
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )

    return LaunchDescription([
        background_file,
        rviz_node,
        delayed_detector,
    ])
