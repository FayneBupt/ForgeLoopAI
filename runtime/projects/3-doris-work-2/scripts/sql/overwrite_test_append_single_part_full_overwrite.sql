-- @VERIFY: ENABLE
-- 1. 清理数据
INSERT OVERWRITE TABLE paimon_1.doris_paimon.append_single_part VALUES 
(1, 'a', 10, '20240101'), 
(2, 'b', 20, '20240101'), 
(3, 'c', 30, '20240102');

-- 2. 插入新数据校验功能
INSERT OVERWRITE TABLE paimon_1.doris_paimon.append_single_part VALUES 
(1000, 'new_a', 1, '20240101'), 
(2000, 'new_b', 2, '20240102');

-- 3. 打印明细验证结果
-- @EXPECT: RESULT
-- 1000, new_a, 1, 20240101
-- 2000, new_b, 2, 20240102
SELECT * FROM paimon_1.doris_paimon.append_single_part ORDER BY c1;