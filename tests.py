#!/usr/bin/env python3
#behöver specifera annars får qemu problem att förstå att det är python
import subprocess
import sys


#denna grund borde passa bra för att sedan kunna utöka till senare labbar (förhoppningsvis, har ej kollat)
#speciellt därför man ska specifera maskin som ska köras då exempelvis i labb 6 för att testa dns kan jag specifera
#server och även köra dns tester :D
# -------------------- Helper functions --------------------

def run_command(command):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def ping_test(ip):
    """Ping a given IP address and return True (0) if successful."""
    command = f"ping -c 1 {ip}"
    return subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0

# -------------------- Tests för alla --------------------

def test_network_settings(expected_ip, expected_netmask, expected_gateway):
    """Check if the machine has the correct IP, netmask, and gateway."""
    ip_output = run_command("ip addr show")
    route_output = run_command("ip route show")
    
   
    # funkade ej förut, eftersom exempelvis /24 i slutet men detta är mycket "snyggare" än att bara ändra expected ip
    mask_length = sum(bin(int(x)).count('1') for x in expected_netmask.split('.'))
    expected_cidr = f"{expected_ip}/{mask_length}"
    
    #check ip +netmask
    ip_test = expected_cidr in ip_output
    
    # Check gateway
    gateway_test = f"default via {expected_gateway}" in route_output if expected_gateway else True

    return ip_test, gateway_test


def test_hostname(expected_hostname):
    """Check if the machine has the correct hostname."""
    hostname = run_command("hostname")
    return hostname == expected_hostname

def test_reach_router(router_ip):
    """Check if the machine can reach the router."""
    return ping_test(router_ip)

# -------------------- Tests specifika till router --------------------

def test_reach_external_ip(external_ip="8.8.8.8"):
    """Check if the router can reach an external IP."""
    return ping_test(external_ip)

def test_ip_forwarding():
    """Check if IP forwarding is enabled on the router."""
    ip_forward = run_command("sysctl net.ipv4.ip_forward")
    return ip_forward == "net.ipv4.ip_forward = 1"

def test_ip_masquerading(interface="ens3"):
    """Check if IP masquerading is set up on the router."""
    nft_output = run_command("nft list ruleset")
    masquerade_rule = f"oifname \"{interface}\" masquerade"
    return masquerade_rule in nft_output

# -------------------- Main test function --------------------

def run_tests(machine_name):
    # definera för varje maskin
    machines = {
        "client-1": {
            "expected_ip": "10.0.0.2",
            "expected_netmask": "255.255.255.0",
            "expected_gateway": "10.0.0.1",
            "expected_hostname": "client-1"
        },
        "client-2": {
            "expected_ip": "10.0.0.3",
            "expected_netmask": "255.255.255.0",
            "expected_gateway": "10.0.0.1",
            "expected_hostname": "client-2"
        },
        "server": {
            "expected_ip": "10.0.0.4",
            "expected_netmask": "255.255.255.0",
            "expected_gateway": "10.0.0.1",
            "expected_hostname": "server"
        },
        "router": {
            "expected_ip": "10.0.0.1",
            "expected_netmask": "255.255.255.0",
            "expected_gateway": None, #router har ej en gateway
            "expected_hostname": "gw"
        }
    }

    # kolla om den existerar
    if machine_name not in machines:
        print(f"Error: Unknown machine '{machine_name}'")
        sys.exit(1)

   
    config = machines[machine_name]
    router_ip = "10.0.0.1"  
    external_ip = "8.8.8.8"  

    # kör
    print(f"Running tests for {machine_name}:")
    
    ip_test, gateway_test = test_network_settings(config["expected_ip"], config["expected_netmask"], config["expected_gateway"])
    print(f" - IP and Netmask Test: {'Pass' if ip_test else 'Fail'}")
    print(f" - Gateway Test: {'Pass' if gateway_test else 'Fail'}")
    
    hostname_test = test_hostname(config["expected_hostname"])
    print(f" - Hostname Test: {'Pass' if hostname_test else 'Fail'}")
    
    router_reach_test = test_reach_router(router_ip)
    print(f" - Reach Router Test: {'Pass' if router_reach_test else 'Fail'}")
    
    # kör mer för router
    if machine_name == "router":
        print("\nRunning additional tests specific to the router:")
        
        external_reach_test = test_reach_external_ip(external_ip)
        print(f" - Reach External IP Test: {'Pass' if external_reach_test else 'Fail'}")
        
        ip_forwarding_test = test_ip_forwarding()
        print(f" - IP Forwarding Test: {'Pass' if ip_forwarding_test else 'Fail'}")
        
        masquerading_test = test_ip_masquerading()
        print(f" - IP Masquerading Test: {'Pass' if masquerading_test else 'Fail'}")



if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: ./tests.py <machine_name>")
        sys.exit(1)
    
    machine_name = sys.argv[1]
    run_tests(machine_name)