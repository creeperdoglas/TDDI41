#!/usr/bin/env python3
import os
import random
import string
import subprocess
import sys


def generate_username(full_name):
    parts = full_name.split()
    if len(parts) >= 2:
        username = (parts[0][0] + parts[1]).lower()
    else:
        username = parts[0].lower()

    username = ''.join(filter(str.isalnum, username))[:8]

    # Lägg till suffix om användarnamnet redan finns i LDAP
    original_username = username
    counter = 0
    while ldap_user_exists(username):
        counter += 1
        suffix = f"{counter:02d}"  # Tvåsiffrigt suffix
        username = original_username[:6] + suffix

    return username


def ldap_user_exists(username):
    """Kontrollera om en användare redan finns i LDAP."""
    try:
        result = subprocess.run(
            ['ldapsearch', '-x', '-b', 'ou=users,dc=grupp13,dc=liu,dc=se', f'(uid={username})'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Timeout vid kontroll av användare: {username}")
        return False
    except Exception as e:
        print(f"Ett fel uppstod vid kontroll av användare {username}: {e}")
        return False


def generate_password(length=12):
    characters = string.ascii_letters + string.digits + "!@#$%^&*()-_+="
    return ''.join(random.choices(characters, k=length))


def get_uid_from_ldap(username):
    """
    Hämtar UID för en användare från LDAP efter att den har skapats.
    """
    try:
        result = subprocess.run(
            ['ldapsearch', '-x', '-b', 'ou=users,dc=grupp13,dc=liu,dc=se', f'(uid={username})', 'uidNumber'],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("uidNumber:"):
                return int(line.split(":")[1].strip())
        print(f"UID för användare {username} hittades inte.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Fel vid hämtning av UID från LDAP för {username}: {e}")
        sys.exit(1)


def create_home_directory(home_directory, username, uid):
    full_path = os.path.join(home_directory, username)
    try:
        os.makedirs(full_path, exist_ok=True)
        print(f"Hemkatalog {full_path} skapad.")

        # Sätt rättigheter med UID och GID (samma som UID här)
        subprocess.run(['chown', '-R', f'{uid}:{uid}', full_path], check=True)
        print(f"Ägare och rättigheter satt för {full_path} med UID:GID {uid}:{uid}.")
    except Exception as e:
        print(f"Fel vid skapande av hemkatalog {full_path}: {e}")
        sys.exit(1)


def add_user_to_ldap(username, password, home_directory):
    print(f"Lägger till användare {username} i LDAP...")

    try:
        # Skapa användarpost i LDAP
        subprocess.run(['ldapadduser', username, 'users'], check=True)
        print(f"Användare {username} tillagd i LDAP.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid skapande av användare {username} i LDAP: {e}")
        sys.exit(1)

    # Hämta UID från LDAP
    uid = get_uid_from_ldap(username)

    try:
        # Sätt lösenord
        password_input = f"{password}\n{password}\n"
        subprocess.run(['ldapsetpasswd', username], input=password_input, text=True, check=True)
        print(f"Lösenord för användare {username} satt i LDAP.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid sättande av lösenord för {username}: {e}")
        sys.exit(1)

    try:
        with open('/etc/ldapscripts/ldapscripts.passwd', 'r') as secret_file:
            ldap_password = secret_file.read().strip()  # 
        # Uppdatera automount-poster
        automount_dn = f"cn={username},ou=auto.home,ou=automount,ou=users,dc=grupp13,dc=liu,dc=se"
        automount_info = f"-fstype=nfs,rw,sync,vers=4 server.grupp13.liu.se:{home_directory}/{username}"

        ldif_content = f"""
dn: {automount_dn}
objectClass: automount
objectClass: top
cn: {username}
automountInformation: {automount_info}
"""
        subprocess.run([
            'ldapadd',
            '-x',
            '-D', 'cn=admin,dc=grupp13,dc=liu,dc=se',
            '-w', ldap_password
        ], input=ldif_content, text=True, check=True)
        print(f"Automount-poster för {username} uppdaterad.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid uppdatering av automount för {username}: {e}")
        sys.exit(1)

    # Skapa hemkatalogen lokalt med den hämtade UID
    create_home_directory(home_directory, username, uid)

    print(f"Användare '{username}' har skapats med lösenord: {password}")
    print(f"Hemkatalog för användare '{username}' är: {home_directory}/{username}")


def main():
    if len(sys.argv) != 2:
        print(f"Användning: {sys.argv[0]} <fil med namn>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, 'r') as file:
            names = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Filen '{filename}' hittades inte!", file=sys.stderr)
        sys.exit(1)

    for name in names:
        username = generate_username(name)
        password = generate_password()

        # Välj hemkatalog slumpmässigt mellan /home1 och /home2
        home_directory = random.choice(['/home1', '/home2'])

        add_user_to_ldap(username, password, home_directory)


if __name__ == "__main__":
    main()
