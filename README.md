# StarLine 2026 Turtlebot Detector

Детекция и локализация Turtlebot2 в облаках точек Livox MID-360 для квалификационного задания HSL26.

## Идея

Лидар и окружение считаются неподвижными. Сначала строится воксельная модель пустой сцены, потом из текущего облака вычитается фон. Оставшиеся точки объединяются в кластеры. Самый большой кластер считается Turtlebot2.

Схема:

```text
пустая сцена -> background_voxels.npz
текущее облако -> вычитание фона -> /foreground_cloud
foreground -> кластеры
самый большой кластер -> /turtlebot_cluster
центр кластера -> TF detected_turtlebot
```

## Демонстрация

<video src="demo/Screencast%20from%202026-07-11%2003-44-30.webm" controls width="100%"></video>

<video src="demo/Screencast%20from%202026-07-11%2003-47-41.webm" controls width="100%"></video>

<video src="demo/Screencast%20from%202026-07-11%2003-48-22.webm" controls width="100%"></video>

<video src="demo/Screencast%20from%202026-07-11%2003-50-10.webm" controls width="100%"></video>

<video src="demo/Screencast%20from%202026-07-11%2003-53-13.webm" controls width="100%"></video>

## Структура проекта

```text
StarLine_2026/
├── README.md
├── docker-compose.yml
├── background_voxels.npz
├── demo/
│   └── *.webm
├── empty_scene/
├── HSL26-ros2_bags/
└── src/
    └── detector/
        ├── detector/
        │   ├── __init__.py
        │   ├── background_builder.py
        │   └── detector.py
        ├── package.xml
        ├── setup.cfg
        └── setup.py
```

## Docker

Запуск контейнера:

```bash
cd ~/my_project/StarLine_2026

export LOCAL_UID=$(id -u)
export LOCAL_GID=$(id -g)

docker compose up -d
docker compose exec starline bash
```

Внутри контейнера:

```bash
source /opt/ros/humble/setup.bash
```

Если MCAP bag-файлы не читаются:

```bash
apt-get update
apt-get install -y ros-humble-rosbag2-storage-mcap
```

## Сборка

```bash
cd /workspace/StarLine_2026

source /opt/ros/humble/setup.bash

rm -rf build/detector install/detector log
colcon build --symlink-install --packages-select detector

source install/setup.bash
```

## Проверка bag-файла

```bash
ros2 bag info HSL26-ros2_bags/rosbag2_2026_06_27-18_43-mov_01
```

Запуск bag-файла:

```bash
ros2 bag play HSL26-ros2_bags/rosbag2_2026_06_27-18_43-mov_01 --storage mcap --loop
```

Основной топик облака:

```text
/livox/lidar
```

## Построение фона

Фон строится по записям пустой сцены, где Turtlebot2 не виден.

Терминал 1:

```bash
cd /workspace/StarLine_2026

source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run detector background_builder \
  --ros-args \
  -p cloud_topic:=/livox/lidar \
  -p output:=/workspace/StarLine_2026/background_voxels.npz \
  -p voxel_size:=0.05 \
  -p frames:=150 \
  -p min_range:=0.2 \
  -p max_range:=3.0
```

Терминал 2:

```bash
cd /workspace/StarLine_2026

source /opt/ros/humble/setup.bash

ros2 bag play empty_scene/empty_scene_1
ros2 bag play empty_scene/empty_scene_2
ros2 bag play empty_scene/empty_scene_3
ros2 bag play empty_scene/empty_scene_4
```

После этого создаётся файл:

```text
background_voxels.npz
```

## Запуск детектора

Терминал 1:

```bash
cd /workspace/StarLine_2026

source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run detector detector \
  --ros-args \
  -p cloud_topic:=/livox/lidar \
  -p background:=/workspace/StarLine_2026/background_voxels.npz \
  -p foreground_topic:=/foreground_cloud \
  -p cluster_topic:=/turtlebot_cluster \
  -p child_frame_id:=detected_turtlebot \
  -p background_neighbor_radius:=1 \
  -p cluster_neighbor_radius:=2 \
  -p min_cluster_points:=10 \
  -p tracking_alpha:=0.2
```

Терминал 2:

```bash
cd /workspace/StarLine_2026

source /opt/ros/humble/setup.bash

ros2 bag play HSL26-ros2_bags/rosbag2_2026_06_27-18_43-mov_01 --storage mcap --loop
```

Терминал 3:

```bash
source /opt/ros/humble/setup.bash
rviz2
```

## RViz

Добавить отображения:

```text
PointCloud2 -> /livox/lidar
PointCloud2 -> /foreground_cloud
PointCloud2 -> /turtlebot_cluster
TF
```

Рекомендуемые настройки для `PointCloud2`:

```text
Reliability Policy: Best Effort
Style: Points
Size (Pixels): 3-5
Decay Time: 0.1
```

`Fixed Frame` нужно поставить равным frame облака. Проверить frame можно так:

```bash
ros2 topic echo /livox/lidar --once --field header.frame_id
```

## Публикуемые данные

```text
/foreground_cloud
```

Облако после вычитания статического фона.

```text
/turtlebot_cluster
```

Самый большой связный foreground-кластер.

```text
/tf
```

TF от frame лидара к `detected_turtlebot`.

Проверка TF:

```bash
ros2 run tf2_ros tf2_echo livox detected_turtlebot
```

Вместо `livox` нужно указать реальный frame из `/livox/lidar`.

## Основные параметры

| Параметр | Значение | Описание |
|---|---:|---|
| `voxel_size` | `0.05` | Размер вокселя фона |
| `min_range` | `0.2` | Минимальная дальность точки |
| `max_range` | `3.0` | Максимальная дальность точки |
| `background_neighbor_radius` | `1` | Радиус проверки соседних вокселей фона |
| `cluster_neighbor_radius` | `2` | Радиус связности точек в кластере |
| `min_cluster_points` | `10` | Минимальный размер кластера |
| `tracking_alpha` | `0.2` | Сглаживание позиции TF |

## Алгоритм

1. `background_builder.py` собирает точки пустой сцены.
2. Каждая точка переводится в индекс вокселя.
3. Занятые воксели сохраняются в `background_voxels.npz`.
4. `detector.py` читает текущее облако `/livox/lidar`.
5. Точки, совпавшие с фоном, удаляются.
6. Оставшиеся точки публикуются в `/foreground_cloud`.
7. Foreground-точки объединяются в связные кластеры.
8. Самый большой кластер публикуется в `/turtlebot_cluster`.
9. Центр bounding box выбранного кластера публикуется как TF `detected_turtlebot`.

## Ограничения

Метод рассчитан на статичный лидар и статичное окружение. Если лидар или сцена смещаются, фон нужно перестраивать или добавлять совмещение облаков.