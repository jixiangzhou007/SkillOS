# Python日志记录基础教程

**来源**: https://docs.python.org/3/howto/logging.html
**类型**: 技术教程

本文的核心论点是：Python 的 logging 模块是比 print() 更专业、更灵活的日志记录工具，适用于需要跟踪程序运行时事件、进行状态监控或故障排查的场景。作者通过对比不同任务的最佳工具（如 print() 用于普通输出，warnings.warn() 用于可避免的警告），以及详细解释日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）的适用场景，论证了 logging 模块在事件严重性分级、输出格式化和持久化存储方面的优势。结论是：对于大型或生产级程序，开发者应显式创建 Logger 对象并配置其行为（如设置日志级别、输出到文件），而非依赖默认的根日志记录器。