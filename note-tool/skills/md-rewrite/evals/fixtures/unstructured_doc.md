# 技术文档

本文档介绍了一个技术系统。

系统架构

系统采用微服务架构，包含以下服务：

- 用户服务
- 订单服务
- 支付服务

用户服务负责用户管理。

订单服务负责订单处理。

支付服务负责支付处理。

技术栈

后端使用 Java + Spring Boot。

数据库使用 MySQL + Redis。

消息队列使用 RabbitMQ。

部署

支持 Docker 容器化部署。

支持 Kubernetes 编排。

监控

使用 Prometheus 进行监控。

使用 Grafana 进行可视化。
