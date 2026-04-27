# Ado_Jk Blog
一个基于FastAPI的个人博客系统，面对个人内容发布、用户互动场景开发。
当前项目定位：个人博客+Python Web后端练习项目。

## 项目简介
Ado_Jk Blog 是一个Python Web单体应用，后续用FastAPI构建接口和页面路由，数据库用SQLAlchemy ORM，页面渲染使用Jinjia2模板。项目支持文章展示、用户注册登录、头像上传、文章上传、文章点赞、评论发布、评论点赞、评论实时推送等功能。

## 技术栈
Web框架： FastAPI，Uvicorn
ORM： SQLAlchemy
数据库： SQlite/MySQL
数据库迁移： Alembic
模板渲染： Jinja2
参数校验： Pydantic，pydantic-settings
用户认证： PyJWT，passlib[bcrypt]
缓存扩展： Redis
实时通信： Server-Sent Events
测试： pytest，httpx
代码检查： Ruff

## 核心功能
### 1.用户认证模块
用户注册/ 用户登录/ Cookie保存在access token/ refresh token续期/ 退出登录/ 头像上传与修改/ 密码哈希存储/ 登陆失败审计日志
#### 2.文章模块
文章列表展示/ 文章详情接口/ 文章点赞、取消点赞/ 文章软删除/ 文章技术标签分类/ 文章封面图字段预留
#### 3.评论模块
评论分页查询/ 评论发布、编辑、删除、点赞、取消点赞/ 支持父子评论结构/ 评论内容长度限制/ 评论接口限流/ SSE实时推送评论新增、修改、删除、点赞事件
### 4.
