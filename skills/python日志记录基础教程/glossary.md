# 术语表: Python日志记录基础教程

## logging
一种跟踪软件运行时事件的手段，开发者通过添加日志调用来记录事件的发生。

关联: Logger, 日志级别

## Logger
通过 logging.getLogger(__name__) 创建的日志记录器对象，用于调用 debug()、info()、warning()、error() 和 critical() 等方法记录事件。

关联: logging, 日志级别

## 日志级别
开发者赋予事件的严重程度等级，用于区分事件的重要性。标准级别从低到高包括 DEBUG、INFO、WARNING、ERROR、CRITICAL。

关联: DEBUG, INFO, WARNING, ERROR, CRITICAL

## DEBUG
最低的日志级别，用于提供详细信息，通常仅在诊断问题时有用。

关联: 日志级别

## INFO
日志级别之一，用于确认程序按预期运行。

关联: 日志级别

## WARNING
日志级别之一，表示发生了意外情况，或暗示即将出现问题（例如“磁盘空间低”），但软件仍按预期工作。默认的日志级别为 WARNING，意味着只有此级别及更严重的事件会被跟踪。

关联: 日志级别

## ERROR
日志级别之一，表示由于更严重的问题，软件无法执行某些功能。

关联: 日志级别

## CRITICAL
最高的日志级别，表示严重错误，表明程序本身可能无法继续运行。

关联: 日志级别

## print()
Python 内置函数，用于在控制台输出普通信息，适合命令行脚本或程序的常规使用场景。

关联: logging

## warnings.warn()
用于在库代码中发出可避免的运行时警告，提示客户端应用程序应修改以消除该警告。

关联: logging

## 根日志记录器
默认的日志记录器，当未显式创建 Logger 对象时使用。其默认级别为 WARNING。

关联: Logger, 日志级别
