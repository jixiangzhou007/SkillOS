# 何时使用日志记录（与 print() 的对比）

通过任务对比表格，明确区分 print()、warnings.warn() 和 logging 方法各自的适用场景，帮助开发者选择正确的工具。

## 要点
- 普通控制台输出应使用 print()
- 库中可避免的警告应使用 warnings.warn()
- 正常操作事件、错误报告等应使用 logger 的 info()、error() 等方法
