# 数据图读取复现

冻结产物：bfe379b1c7679626fac0cf675d69b5395a8f88a7。Windows，实际Python 3.14.3，未容器化，无运行期外部服务或网络。解释器、包版本和实际import路径见environment-reviewed.json。

检出冻结版本，按记录安装同版Python和依赖，PYTHONPATH指向检出目录、src、lib。各命令JSON保留真实argv/cwd/输出/退出码；按新检出目录替换原机路径，不改断言。acceptance-r1为215项原有jsonpickle回归和42项独立用例，均通过。final-subset-r1独立运行与原轨最终相同的相关模块及两个模块doctest，共409通过，包含72项新测试；不是全可选扩展套件。

contexts-r1独立2通过/3失败。旧context忽略data_only开关导致两条探针进入旧对象/还原分支；另一失败是直接restore(tuple)不拒绝。native-context-r1不替换库钩子，只提供本文件中无害Counted类作classes映射；默认context拒绝且事件为空，普通Unpickler context使decode和loads调用__new__/__setstate__并返回Counted，2通过/2失败。demo_context.py同时显示这些真实副作用和tuple返回，退出1。多个context表现同根因不重复扣分。

fixture-provenance-r1保留开跑前预备夹具及正式验收前修订：py/unknown不是已定义保留标记，按题面应原样保留，旧过严断言从未用于评分。原轨全套收集缺可选依赖，筛选广套有3个时区/Decimal失败，原轨对起点做了同范围对照；独立评分没有将这些失败算作新改动问题，也没有宣称全套通过。

run-provenance-r1记录首次请求HTTP400、无工具动作且无有效答复的故障，不评分。相同配置恢复探测后仅新会话工程重试1次，题面/起点/三处high与1M配置不变；有效会话轨迹附件只有一个。

product-demo-r1和native-context-r1的demo及控制台为独立验证工具，实际调用冻结库，不冒充模型产物界面。recorded-runtime-r1保留74.92秒连续录屏的命令和真实输出，退出码[0,0,1]，失败保留。
