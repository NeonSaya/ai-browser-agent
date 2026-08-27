'''
主程序入口
'''

import sys
from webagent.main import cmd_self_check,cmd_browser_smoke,cmd_perceive_smoke

def main()->int:
    if len(sys.argv) <2:
        print("Usage: python -m webagent <command>")
        print("Commands:")
        print("  self-check: 验证核心层所有组件能正常工作")
        print("  browser-smoke: 浏览器冒烟测试")
        print("  perceive-smoke: 感知层冒烟测试")
        return 1
    command=sys.argv[1]
    if command=="self-check":
        return cmd_self_check()
    elif command=="browser-smoke":
        return cmd_browser_smoke()
    elif command=="perceive-smoke":
        return cmd_perceive_smoke()
    else:
        print(f"Unknown command: {command}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
