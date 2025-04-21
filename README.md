# RSS文章自动获取并转发到Cubox

## 背景
由于[官方推荐](https://help.cubox.pro/save/89d3/)的github action每次更新之后rerun的时候，都会重复推送所有订阅
但是intergrately、ifttt等第三方服务又存在不稳定或者性价比不高的情况，这里重新更新下功能

## 功能实现
1. 通过 RSS 订阅源地址发送文章至 Cubox 指定收藏夹，可同步添加标签。
2. 通过时间戳自动判断同步文章的范围，上次同步完成的时间点为t，当前时间点为n，则每次同步的文章只限于`( t->n ) `之间的文章。
3. 可以用容器跑，指定环境变量即可


## 使用步骤

### 容器运行
1. 修改docker-compose.yaml中的CUBOX_API为你的订阅链接
2. 修改timestramp.txt中的同步起始时间点，或留空默认取 ( 2024-01-01 -> now ) 的rss
3. `docker-compose up` 启动容器即可

### 本地运行
1. 克隆仓库到本地，安装依赖`pip3 install feedparser requests`
2. 在 [config.py](/config.py) 中设置 Cubox API、标签、收藏夹和订阅源地址。
3. 运行：
    ```shell
    python main.py
    ```
