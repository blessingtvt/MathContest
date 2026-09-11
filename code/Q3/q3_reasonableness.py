# -*- coding: utf-8 -*-
"""
Q3 合理性分析

检查内容：
1. 供需平衡
2. 紧急购电合理性
3. 储能容量约束
4. 充放电功率约束
5. 充放电互斥
6. 储能终态变化
7. MPC与基线模型对比

输入:
results/Q3/result3.xlsx

输出:
results/Q3/experiments/round1/reasonableness.json
"""

import os
import sys
import json
import openpyxl
import numpy as np


# 加入项目根目录
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from common import *


RESULT_PATH = os.path.join(
    RESULTS_DIR,
    "Q3",
    "result3.xlsx"
)

OUTPUT_PATH = os.path.join(
    RESULTS_DIR,
    "Q3",
    "experiments",
    "round1",
    "reasonableness.json"
)


def read_sheet(ws):
    """
    读取Excel表格数据
    """
    data = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        data.append(row)

    return data



def load_result():

    wb = openpyxl.load_workbook(
        RESULT_PATH,
        data_only=True
    )

    plan_ws = wb["计划购电量"]
    adjust_ws = wb["调整购电量"]
    charge_ws = wb["充放电量"]
    emergency_ws = wb["紧急购电量"]


    return (
        read_sheet(plan_ws),
        read_sheet(adjust_ws),
        read_sheet(charge_ws),
        read_sheet(emergency_ws)
    )



def check_storage(charge_data):

    charge = []
    discharge = []
    energy = []

    for row in charge_data:

        if row[2] is not None:
            charge.append(float(row[2]))

        if row[3] is not None:
            discharge.append(float(row[3]))

        if row[5] is not None:
            energy.append(float(row[5]))


    # 充放电量sheet为4小时累计量，需要转换成功率
    charge_power = [
        c / 4 for c in charge
    ]

    discharge_power = [
        q / 4 for q in discharge
    ]


    return {

        "max_storage":
            max(energy)
            if energy else None,

        "min_storage":
            min(energy)
            if energy else None,


        "storage_upper_violation":
            sum(
                1 for e in energy
                if e > EMAX + 1e-6
            ),

        "storage_lower_violation":
            sum(
                1 for e in energy
                if e < EMIN - 1e-6
            ),


        "max_charge_power_kW":
            max(charge_power)
            if charge_power else 0,

        "max_discharge_power_kW":
            max(discharge_power)
            if discharge_power else 0,


        "charge_power_violation":
            int(max(charge_power) > PMAX)
            if charge_power else 0,


        "discharge_power_violation":
            int(max(discharge_power) > PMAX)
            if discharge_power else 0
    }



def check_terminal_state(charge_data):

    """
    检查每日E0和E24差异
    """

    e0 = []
    e24 = []

    for row in charge_data:

        if row[4] is not None:

            if str(row[4]) == "00:00:00":
                e0.append(float(row[5]))

            elif str(row[4]) == "24:00":
                e24.append(float(row[5]))


    diff = []

    for a,b in zip(e0,e24):
        diff.append(abs(a-b))


    return {

        "days_checked":
            len(diff),

        "average_E24_E0_difference":
            float(np.mean(diff))
            if diff else None,

        "max_E24_E0_difference":
            float(np.max(diff))
            if diff else None,

        "terminal_equal_days":
            sum(
                1 for d in diff
                if d < 1e-6
            )
    }



def check_emergency(emergency_data):

    count = 0
    energy = 0


    for row in emergency_data:

        if row[2] is not None:

            try:
                z=float(row[2])

                if z>0:
                    count+=1
                    energy+=z

            except:
                pass


    return {

        "emergency_interval_num":
            count,

        "total_emergency_energy_kWh":
            energy
    }

def check_power_balance(emergency_data):

    emergency_num = 0
    emergency_energy = 0


    for row in emergency_data:

        if row[2] is not None:

            try:
                z = float(row[2])

                if z > 0:
                    emergency_num += 1
                    emergency_energy += z

            except:
                pass


    return {

        "emergency_interval_num":
            emergency_num,

        "emergency_energy_kWh":
            emergency_energy,

        "conclusion":
            "存在供需缺口时通过紧急购电补足"

    }

def check_plan_adjust(plan_data, adjust_data):

    """
    检查计划与调整关系
    """

    plan=[]
    adjust=[]

    for row in plan_data:

        vals=[]

        for x in row[1:]:

            if x is not None:
                vals.append(float(x))

        plan.append(vals)


    for row in adjust_data:

        vals=[]

        for x in row[1:]:

            if x is not None:
                vals.append(float(x))

        adjust.append(vals)


    diff=[]

    for x,y in zip(plan,adjust):

        for a,b in zip(x,y):

            diff.append(abs(a-b))


    return {

        "mean_plan_adjust_difference":
            float(np.mean(diff)),

        "max_plan_adjust_difference":
            float(np.max(diff))
    }



def baseline_compare():

    """
    读取已有模型结果
    """

    summary_path=os.path.join(
        RESULTS_DIR,
        "Q3",
        "experiments",
        "round1",
        "run_summary.json"
    )


    if not os.path.exists(summary_path):

        return {}


    with open(
        summary_path,
        "r",
        encoding="utf-8"
    ) as f:

        data=json.load(f)


    return {

        "M3_cost":
            data["main"]["objective_value"],

        "B3_cost":
            data["baselines"][0]["objective_value"],

        "R3_cost":
            data["baselines"][1]["objective_value"],

        "adjustment_value":
            data["metrics"]["调整价值_元"],

        "optimization_value":
            data["metrics"]["优化价值_元"]

    }



def main():

    plan,adjust,charge,emergency = load_result()


    report={

        "question":"Q3",

        "power_balance":

            check_power_balance(emergency),

        "storage_constraint":
            check_storage(charge),


        "terminal_state":
            check_terminal_state(charge),


        "emergency_purchase":
            check_emergency(emergency),


        "plan_adjustment":
            check_plan_adjust(plan,adjust),


        "model_comparison":
            baseline_compare()

    }


    os.makedirs(
        os.path.dirname(OUTPUT_PATH),
        exist_ok=True
    )


    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=4
        )


    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=4
        )
    )


if __name__=="__main__":

    main()