"""
demo.py - Interactive demo controller

Lets you trigger and fix incidents across your fake services
during a live demo or recording. Run this in a terminal and
press keys to control the demo.

Usage: python demo.py
"""

import time
import urllib.request

SERVICES = {
    "1": ("payment-service",  8001),
    "2": ("auth-service",     8002),
    "3": ("checkout-service", 8003),
}


def call(port, path):
    try:
        url = f"http://localhost:{port}/{path}"
        res = urllib.request.urlopen(url, timeout=3)
        return res.read().decode()
    except Exception as e:
        return f"Error: {e}"


def status():
    print("\n── Service Status ───────────────────────────────")
    for key, (name, port) in SERVICES.items():
        health = call(port, "health")
        icon = "✅" if health == "ok" else "🔴"
        print(f"  [{key}] {icon}  {name} (port {port})")
    print("─────────────────────────────────────────────────\n")


def menu():
    print("\n══ INCIDENT DEMO CONTROLLER ═════════════════════")
    print("  [1] Break payment-service")
    print("  [2] Break auth-service")
    print("  [3] Break checkout-service")
    print("  [f] Fix all services")
    print("  [s] Show status")
    print("  [q] Quit")
    print("═════════════════════════════════════════════════")


def main():
    print("\n⚡ IncidentAI Demo Controller")
    print("Waiting ~15 seconds after breaking a service")
    print("for Prometheus to detect and IncidentAI to diagnose.\n")

    status()

    while True:
        menu()
        choice = input("  Choose: ").strip().lower()

        if choice in SERVICES:
            name, port = SERVICES[choice]
            result = call(port, "break")
            print(f"\n💥 {result}")
            print(f"   → Watch Slack in ~15-30 seconds for the diagnosis")
            print(f"   → Or check http://localhost:5173/dashboard")

        elif choice == "f":
            for name, port in SERVICES.values():
                result = call(port, "fix")
                print(f"  ✅ Fixed {name}")
            print("\nAll services healthy. Give it 30s to clear.")

        elif choice == "s":
            status()

        elif choice == "q":
            print("Bye!")
            break

        else:
            print("Unknown command")


if __name__ == "__main__":
    main()