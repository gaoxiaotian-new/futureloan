import json
import os
import unittest
from decimal import Decimal

import ddt

from common.excel_handler import ExcelHandler
from common.requests_handler import visit
from middleware import handler

env_data = handler.MiddleHandler()
cases = env_data.excel.read_data("invest")
logger = env_data.logger


@ddt.ddt
class TestInvest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 登录
        cls.token = env_data.token
        cls.member_id = env_data.member_id


    def setUp(self):
        self.db = env_data.db_class()
        setattr(env_data,"loan_id",env_data.add_project())
        self.loan_id = env_data.loan_id
        self.pass_loan_id = env_data.audit()
        env_data.recharge()

    def tearDown(self):
        self.db.close()

    @ddt.data(*cases)
    def test_invest(self, case_info):
        """测试投资接口"""
        # 查询投资用户在invest表中的投资记录
        before_data = self.db.query(
            "SELECT COUNT(*) as berfore_num FROM invest WHERE member_id={};".format(self.member_id))
        before_num = before_data["berfore_num"]

        # 查询投资用户的余额
        before_info = self.db.query(
            "SELECT * FROM member WHERE id = {}".format(self.member_id)
        )
        before_amount = before_info["leave_amount"]

        # 查询投资用户的交易记录
        before_log_info = self.db.query(
            "SELECT COUNT(*) as before_log_count  FROM financelog WHERE pay_member_id = {}".format(self.member_id)
        )
        before_log_count = before_log_info["before_log_count"]

        logger.info("正在执行第{}条用例：{}".format(case_info["case_id"], case_info["title"]))

        # data = case_info["data"]
        # if "#member_id#" in data:
        #     data = data.replace("#member_id#", str(self.member_id))
        #
        # headers = case_info["headers"]
        # if "#token#" in headers:
        #     headers = headers.replace("#token#", self.token)
        #
        # if "#loan_id#" in data:
        #     data = data.replace("#loan_id#", str(self.pass_loan_id))
        data = env_data.replace_data(case_info["data"])
        headers = env_data.replace_data(case_info["headers"])
        # 访问接口
        resp = visit(
            url=env_data.yaml_data["host"] + case_info["url"],
            method=case_info["method"],
            json=json.loads(data),
            headers=json.loads(headers)
        )
        # 测试用例的路径
        data_path = os.path.join(env_data.config.DATA_PATH, "testcases.xlsx")
        # 开始断言
        try:
            for k, v in json.loads(case_info["expected"]).items():
                self.assertTrue(v == resp[k])
            if resp["code"] == 0:
                # 判断invest表是否增加一条记录
                after_data = self.db.query(
                    "SELECT COUNT(*) as after_num FROM invest WHERE member_id={};".format(self.member_id))
                after_num = after_data["after_num"]
                self.assertTrue(before_num + 1 == after_num)
                # 判断投资之前余额 - 投资金额 == 投资后余额
                after_info = self.db.query(
                    "SELECT * FROM member WHERE id = {}".format(self.member_id)
                )
                after_amount = after_info["leave_amount"]
                self.assertTrue(before_amount - Decimal(str(json.loads(data)["amount"])) == after_amount)
                # 判断financelog表是否新增一条交易记录
                after_log_info = self.db.query(
                    "SELECT COUNT(*) as after_log_count  FROM financelog WHERE pay_member_id = {}".format(self.member_id)
                )
                after_log_count = after_log_info["after_log_count"]
                self.assertTrue(before_log_count + 1 == after_log_count)
            # 断言成功设置result属性为pass
            self.result = "PASS"
            logger.info("第{}条测试用例通过".format(case_info["case_id"]))

        except AssertionError as e:
            self.result = "FAIL"
            logger.error("第{}条测试用例无法通过：{}".format(case_info["case_id"], e))
            raise e
        # 将测试结果写入excel
        finally:
            ExcelHandler(data_path).write(sheet_name="add", row=case_info["case_id"] + 1, column=9,
                                          data=self.result)


if __name__ == '__main__':
    unittest.main()
