from security_attack_module.MITM import MITMAttackScenario
from security_attack_module.DDoS import DDOSAttackScenario
from security_attack_module.BAC.BAC import BACAttackScenario
from utils.storyboard import  Mode, LogConfig
from utils.msglog import log_att_process


def switch_mode(scenario, target, protocol, use_encryption):
    file_path = LogConfig.RUNTIME_REPORT
    scenario_handlers = {
            'MITM': MITMAttackScenario,
            'BAC': BACAttackScenario,
            'DDOS': DDOSAttackScenario,
        }

    # print(f"Switching mode to --{scenario}--- targeting {target}")
    if scenario in scenario_handlers:
        if scenario == 'DDOS':
            print(f"\n +++++++++++++++Mode set to {scenario}+++++++++++++++")
            msg = f"\n +++++++++++++++Mode set to {scenario}+++++++++++++++"
            log_att_process(file_path, msg)
            print("DDOS attack initiated......")
            msg = "DDOS attack initiated......"
            log_att_process(file_path, msg)
            return Mode.Normal, Mode.Normal
        else:
            current_mode = scenario_handlers[scenario](target, protocol, use_encryption)
            print(f"\n +++++++++++++++Mode set to {scenario}, starting attack on target: {target}++++++++++++++++")
            msg = f"\n +++++++++++++++Mode set to {scenario}, starting attack on target: {target}++++++++++++++++"
            log_att_process(file_path, msg)
            current_mode.start_attack()  # Except DDOS

        if not current_mode.success:
            print("Attack failed------------")
            msg = "Attack failed------------"
            log_att_process(file_path, msg)
            return Mode.Normal, Mode.Normal

        return current_mode.bos_mode, current_mode.rpf_mode


    return Mode.Normal, Mode.Normal

