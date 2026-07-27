# StarLine 2026 Turtlebot Detector

## Описание проекта
Данный репозиторий содержит решение квалификационного задания для хакатона StarLine, реализованное на ROS2 Humble. Проект осуществляет детекцию и локализацию Turtlebot2 в облаках точек Livox MID-360.

## Принцип работы
Лидар и окружение считаются неподвижными.

Исходные bag-файлы были проанализированы и обрезаны таким образом, чтобы выделить сегменты записи, в которых мобильный робот отсутствует в поле зрения лидара. Полученные файлы сохранены в папке empty_scene и используются вместе с нодой background_builder.py для построения эталонной воксельной карты окружения, которая сохраняется в файл background_voxels.npz. Далее запускается нода detector.py и исходные bag-файлы. Алгоритм вычитает воксели эталонного фона из текущего облака точек. Оставшиеся точки группируются в кластеры, и самый крупный из них идентифицируется как Turtlebot2. Геометрический центр этого кластера публикуется в ROS2 как TF-трансформация с именем detected_turtlebot.»


## Демонстрация работы

### 1. Исходное облако и вычитание фона

На этом этапе из текущего облака `/livox/lidar` удаляются точки, которые совпадают с заранее построенной воксельной моделью пустой сцены. В результате остаются только новые объекты в сцене.


### 2. Выделение foreground-кластера

Из-за шумов все обнаруженные точки использовать не получится. Нужно провести фильтрацию. Поэтому после вычитания фона оставшиеся точки объединяются в связные кластеры. Кластеры меньше заданного порога отбрасываются как шум.


### 3. Детекция статичного Turtlebot2

Самый большой связный foreground-кластер выбирается как Turtlebot2. Этот кластер публикуется в отдельный топик `/turtlebot_cluster`.

[Screencast from 2026-07-11 03-48-22 (trimmed).webm](https://github.com/user-attachments/assets/abde12f0-7a19-4b40-8fc0-5f52b8a82acd)


### 4. Детекция движущегося Turtlebot2

Тот же алгоритм применяется к bag-файлам, где робот движется. Так как лидар и сцена неподвижны, вычитание статического фона позволяет устойчиво выделять робота во время движения.

[Screencast from 2026-07-11 03-47-41.webm](https://github.com/user-attachments/assets/f881def7-2ba4-4752-93f7-99a2dd0138b0)


### 5. Публикация TF

Вычисляем центр кластера, соответствующего роботу. Эта позиция публикуется как TF `detected_turtlebot`, что позволяет отслеживать положение робота в RViz.

[Screencast from 2026-07-11 03-53-13 (trimmed).webm](https://github.com/user-attachments/assets/43bf2aa6-acf8-4fb0-97cc-b8e55a65f6a2)

## Ограничения

Метод рассчитан на статичный лидар и статичное окружение. Если лидар или сцена смещаются, фон нужно перестраивать или добавлять совмещение облаков.

## Требования к системе
- **Операционная система**: Linux Ubuntu 22.04 
- **ROS 2**: дистрибутив Humble  
- **Python**: 3.10 или выше

**Для установки ROS 2** вы можете воспользоваться данной статьёй:
https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html

Также вам понадобятся дополнительные пакеты ROS 2 и Python, для их установки выполните следующие команды:

**Настройка окружения ROS2 и обновление apt**
```
source /opt/ros/humble/setup.bash
sudo apt update
```
**Установка python-библиотек и инструментов сборки**
```
sudo apt install -y \
  build-essential cmake \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-argcomplete \
  python3-numpy
```
**Установка ROS-пакетов**
```
sudo apt install -y \
  ros-humble-rclpy \
  ros-humble-rclcpp \
  ros-humble-rviz2 \
  ros-humble-sensor-msgs \
  ros-humble-geometry-msgs \
  ros-humble-visualization-msgs \
  ros-humble-std-msgs \
  ros-humble-tf2 \
  ros-humble-tf2-ros \
  ros-humble-tf2-geometry-msgs \
  ros-humble-tf2-sensor-msgs \
  ros-humble-ros2bag \
  ros-humble-rosbag2-storage-mcap\
```
**Настройте rosdep**
```
sudo rosdep init
rosdep update
```

## Установка и настройка репозитория
Все команды выполняются в терминале Linux.

**Клонирование репозитория**
```
git clone https://github.com/YuraKram/StarLine_2026.git

cd StarLine_2026
```
**Скачивание bag-файлов**

Скачайте архив с bag-файлами по ссылке: https://disk.yandex.ru/d/aaqaNpTZLNcLtg

Распакуйте скачанный архив и переместите его в папку StarLine_2026.


**Настройка окружения ROS2**
```
source /opt/ros/humble/setup.bash
```
**Установка зависимостей**
```
rosdep install -i --from-path src --rosdistro humble -y

```
**Сборка пакетов**
```
colcon build
```
**Настройка окружения рабочего пространства**
```
source install/setup.bash
```

## Запуск
Выполните команду:
```
ros2 launch detector detector.launch.py
```
Данная команда запускает ноду detector, которая осуществляет поиск Turtlebot2 и открывает окно rviz2, в котором запускается визуализация кластера точек, соответствующего роботу. 

В другом терминале запустите воспроизведение одного из bag-файлов.

