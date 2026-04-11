-- @VERIFY: ENABLE
-- 1. 清理数据
INSERT OVERWRITE TABLE paimon_1.doris_paimon.append_multi_part VALUES
(1, 'a', 10, '20240101', '10'),
(2, 'b', 20, '20240101', '10'),
(3, 'c', 30, '20240101', '11');

-- 2. 插入新数据校验功能
INSERT OVERWRITE TABLE paimon_1.doris_paimon.append_multi_part 
PARTITION(dt='20240101', hh='10') VALUES
(8888, 'only_partition_overwrite', 888, '20240101', '10');

-- 3. 打印明细验证结果
-- @EXPECT: RESULT
-- 3,c,30,20240101,11
-- 8888,only_partition_overwrite,888,20240101,10
SELECT * FROM paimon_1.doris_paimon.append_multi_part order by c1;
