# 查询契约与虚构数据

按owner过滤，按saved_seq DESC、id DESC稳定排序；下一页严格位于上一页最后一个元组之后，limit=2。只有saved_seq不足以表达同序号的先后。
表、样本和游标全部独立虚构；replay仅在进程内SQLite创建临时表，不读凭证、不连接外部数据库。
