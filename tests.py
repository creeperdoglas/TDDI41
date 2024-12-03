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

# -------------------- Brandvägg Tests för alla--------------------

def test_nftables_active():
    """Check if nftables is active."""
    nft_status = run_command("systemctl is-active nftables")
    return nft_status == "active"

def test_nftables_rules(expected_rules):
    """
    Check if all expected nftables rules are present.
    Ignores extra rules.
    """
    #bryr sig endast om de gemensamma reglerna då router har fler men detta är för att kunna köra på alla system, debug del i form av missing rules då fick fail på router.
    nft_output = run_command("nft list ruleset")
    missing_rules = [rule for rule in expected_rules if rule not in nft_output]
    if missing_rules:
        print("Missing rules:")
        for rule in missing_rules:
            print(f"  - {rule}")
        return False
    return True




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


# -------------------- DNS Tests för alla--------------------
#skrev i början endast att kolla i filen etc/resolv.conf för att kolla vilken nameserver är specifierad, detta är snyggare och bättre dock
#kanske även borde ta bort +trace då trace visar den exakta vägen som tas men tar längre tid än bara dig, än så länge tar testfallen en acceptabel tid att kära dock.
def test_dns_server_used(expected_dns_server):
    """Check which DNS server is being used by performing a dig query."""
    dig_output = run_command("dig +trace google.com")
    return expected_dns_server in dig_output

#assistent sa att det kan vara bra att ha ett test som testar om ex client1 kan dig:a client2. gjort ett allmänt test nu.
def test_dns_query_to_client2():
    """
    Test if the DNS query for client-2.grupp13.liu.se resolves to 10.0.0.3.
    """
    target_hostname = "client-2.grupp13.liu.se"
    expected_ip = "10.0.0.3"

    dig_output = run_command(f"dig +short {target_hostname}")
    if not dig_output:
        print(f"Error: DNS query for {target_hostname} returned no result.")
        return False

    # Kontrollera om resultatet innehåller förväntad IP-adress
    if expected_ip in dig_output:
        return True
    else:
        print(f"Error: DNS query for {target_hostname} returned {dig_output}, expected {expected_ip}.")
        return False


# -------------------- DNS Tests för server --------------------

def test_dns_server_running():
    """Check if the DNS server (named) is running."""
    service_status = run_command("systemctl is-active named")
    return service_status == "active"

def test_dns_zone_files():
    """Check if the DNS server has correct zone files."""
    # Uppdaterade sökvägar för zonfiler
    forward_zone = "/etc/bind/zones/db.grupp13.liu.se"
    reverse_zone = "/etc/bind/zones/db.10.0.0"
    
    # Validera zonfiler med named-checkzone
    forward_check = run_command(f"named-checkzone grupp13.liu.se {forward_zone}")
    reverse_check = run_command(f"named-checkzone 0.0.10.in-addr.arpa {reverse_zone}")
    
    # Kontrollera om båda zonfilerna är giltiga
    return "OK" in forward_check and "OK" in reverse_check

def test_dns_forward_query(hostname, fqdn, expected_ip):
    """Test DNS forward lookup (hostname to IP)."""
    # Gör en DNS-fråga mot servern med dig
    result = run_command(f"dig +short {fqdn}")
    return result.strip() == expected_ip

def test_dns_reverse_query(ip, expected_fqdn):
    """Test DNS reverse lookup (IP to hostname)."""
    # Utför en reverse DNS-fråga med dig
    result = run_command(f"dig +short -x {ip}")
    #ta bort . . tror testet faila förut pga reverse alltid innehåller punkt i slutet? Snyggare att ta bort punkterna än att lägga in punkt i expected
    result = result.strip().rstrip(".")
    expected_fqdn = expected_fqdn.rstrip(".")
    return result.strip() == expected_fqdn


# -------------------- LDAP tester --------------------
def test_service_active(service_name = "nslcd"):
    """Check if a specific service is active."""
    status = run_command(f"systemctl is-active {service_name}")
    return status == "active"


def test_nsswitch_ldap():
    """Verify that NSS is configured to use LDAP for passwd, group, and shadow."""
    try:
        with open("/etc/nsswitch.conf", "r") as file:
            config = file.read()
        passwd_ldap = "passwd:         files systemd ldap" in config
        group_ldap = "group:          files systemd ldap" in config
        shadow_ldap = "shadow:         files ldap" in config
        return passwd_ldap and group_ldap and shadow_ldap
    except FileNotFoundError:
        print("Error: /etc/nsswitch.conf not found!")
        return False


def test_getent_passwd():
    """Verify that getent passwd returns LDAP users."""
    output = run_command("getent passwd")
    if not output:
        print("Error: getent passwd returned no output.")
        return False
    return "melkergustafsson" in output  # känd user


def test_ldapsearch():
    """Verify that LDAP search works."""
    command = "/usr/bin/ldapsearch -x -b 'dc=grupp13,dc=liu,dc=se' -LLL '(objectClass=*)'"

    
    output = run_command(command)
    #la till lite debugg, den funkade ej, så måste lista ut vad
    if output is None or not output.strip():
        print("Error: ldapsearch returned no output.")
        return False

    # Kontrollera om den förväntade DN finns i utdata
    expected_dn = f"dc=grupp13,dc=liu,dc=se"
    if expected_dn not in output:
        print(f"Error: Expected DN '{expected_dn}' not found in ldapsearch output.")
        print(f"ldapsearch output:\n{output}")
        return False

    return True




# -------------------- Main test function --------------------

def run_tests(machine_name):
    # definera för varje maskin
    machines = {
        "client-1": {
            "expected_ip": "10.0.0.2",
            "expected_netmask": "255.255.255.0",
            "expected_gateway": "10.0.0.1",
            "expected_hostname": "client-1",
            "expected_dns_server": "10.0.0.4"
        },
        "client-2": {
            "expected_ip": "10.0.0.3",
            "expected_netmask": "255.255.255.0",
            "expected_gateway": "10.0.0.1",
            "expected_hostname": "client-2",
            "expected_dns_server": "10.0.0.4"
        },
        "server": {
            "expected_ip": "10.0.0.4",
            "expected_netmask": "255.255.255.0",
            "expected_gateway": "10.0.0.1",
            "expected_hostname": "server",
            "expected_dns_server": "10.0.0.4",
            "expected_fqdn": "server.grupp13.liu.se"
        },
        "router": {
            "expected_ip": "10.0.0.1",
            "expected_netmask": "255.255.255.0",
            "expected_gateway": None, #router har ej en gateway
            "expected_hostname": "gw",
            "expected_dns_server": "10.0.0.4"
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

    dns_client2_test = test_dns_query_to_client2()
    print(f" - DNS Query to client-2 Test: {'Pass' if dns_client2_test else 'Fail'}")
    
    router_reach_test = test_reach_router(router_ip)
    print(f" - Reach Router Test: {'Pass' if router_reach_test else 'Fail'}")

    dns_server_used_test = test_dns_server_used(config["expected_dns_server"])
    print(f" - DNS Server Used Test: {'Pass' if dns_server_used_test else 'Fail'}")

    nft_active_test = test_nftables_active()
    print(f" - nftables Active Test: {'Pass' if nft_active_test else 'Fail'}")

    expected_firewall_rules = [
    'ct state established,related accept',  # Tillåt etablerade/relaterade anslutningar
    'ip protocol icmp accept',              # Tillåt ICMP (ping)
    'iif "lo" accept',                        # Tillåt loopback-trafik, notera att "lo" är pga att det blir så när man använder nft list ruleset av någon anledning.
    'tcp dport 22 accept'                   # Tillåt SSH
    ]
    nft_rules_test = test_nftables_rules(expected_firewall_rules)
    print(f" - nftables Rules Test: {'Pass' if nft_rules_test else 'Fail'}")


    
    # kör mer för router
    if machine_name == "router":
        print("\nRunning additional tests specific to the router:")
        
        external_reach_test = test_reach_external_ip(external_ip)
        print(f" - Reach External IP Test: {'Pass' if external_reach_test else 'Fail'}")
        
        ip_forwarding_test = test_ip_forwarding()
        print(f" - IP Forwarding Test: {'Pass' if ip_forwarding_test else 'Fail'}")
        
        masquerading_test = test_ip_masquerading()
        print(f" - IP Masquerading Test: {'Pass' if masquerading_test else 'Fail'}")

    #kör mer för server
    if machine_name == "server":
        print("\nRunning additional tests specific to the DNS server:")
    
         # Testa om DNS-servern (named) körs
        dns_running_test = test_dns_server_running()
        print(f" - DNS Service Running Test: {'Pass' if dns_running_test else 'Fail'}")
    
         # Testa zonfilerna för forward och reverse DNS
        dns_zone_test = test_dns_zone_files()
        print(f" - DNS Zone Files Test: {'Pass' if dns_zone_test else 'Fail'}")
    
        # Testa forward DNS-uppslag (hostname → IP)
        forward_query_test = test_dns_forward_query("server", "server.grupp13.liu.se", "10.0.0.4")
        print(f" - Forward Lookup Test: {'Pass' if forward_query_test else 'Fail'}")
    
        # Testa reverse DNS-uppslag (IP → hostname)
        reverse_query_test = test_dns_reverse_query("10.0.0.4", config["expected_fqdn"])
        print(f" - Reverse Lookup Test: {'Pass' if reverse_query_test else 'Fail'}")

        ldapsearch_test = test_ldapsearch()
        print(f" - ldapsearch test: {'Pass' if ldapsearch_test else 'Fail'}")
    
    #för klienterna
    if machine_name in ["client-1", "client-2"]:
        print("\nRunning additional tests for the clients:")

        service_active_test = test_service_active()
        print(f" - nslcd Service Active Test: {'Pass' if service_active_test else 'Fail'}")

        nsswitch_ldap_test = test_nsswitch_ldap()
        print(f" - NSSwitch Using LDAP Test: {'Pass' if nsswitch_ldap_test else 'Fail'}")

        getent_passwd_test = test_getent_passwd()
        print(f" - getent Finding User Test: {'Pass' if getent_passwd_test else 'Fail'}")



if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: ./tests.py <machine_name>")
        sys.exit(1)
    
    machine_name = sys.argv[1]
    run_tests(machine_name)
