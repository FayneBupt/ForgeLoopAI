-- @VERIFY: ENABLE
-- 1. 清理数据
INSERT OVERWRITE TABLE paimon_1.doris_paimon.append_multi_part VALUES
(1, 'a', 10, '20240101', '10'),
(2, 'b', 20, '20240101', '10'),
(3, 'c', 30, '20240101', '11');


-- 2. 插入新数据校验功能
INSERT OVERWRITE TABLE paimon_1.doris_paimon.append_multi_part
    PARTITION(*)
    SELECT *
    FROM (
        SELECT 8888 AS c1, 'only_partition_overwrite' AS c2, 888 AS c3, '20240101' AS dt, '10' AS hh
    ) t
    WHERE 1 = 0;

-- 3. 打印明细验证结果
-- @EXPECT: RESULT
--1,a, 10, 20240101, 10
--2,b, 20, 20240101, 10
--3,c, 30, 20240101, 11
SELECT * FROM paimon_1.doris_paimon.append_multi_part ORDER BY c1;
