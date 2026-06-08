## library是跨项目通用的，不要乱改
## 构造一个agent可以参考examples
## loop,context_manager,agent这里特意没用基类，也没有具体示例，就是因为这些是高度定制化的
## 所以我加了examples下,用来做示例
## 仔细想想我为什么这么干
## 允许重复，以低耦合为先，各Agent相互隔离，例如两个agent下都有tool_call_loop.py，只要命名相同，就代表同一loop。
## examples下的包不要导到其它模块里去