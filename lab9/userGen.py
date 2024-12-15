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

    while user_exists(username):
        suffix = ''.join(random.choices(string.digits, k=2))
        username = username[:6] + suffix

    return username


def generate_password(length=12):
    characters = string.ascii_letters + string.digits + "!@#$%^&*()-_+="
    return ''.join(random.choices(characters, k=length))


def user_exists(username):
    try:
        result = subprocess.run(['id', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Timeout vid kontroll av användare: {username}")
        return False
    except Exception as e:
        print(f"Ett fel uppstod vid kontroll av användare {username}: {e}")
        return False
def get_user_ids(username):
    try:
        # Använd `id -u` och `id -g` för att hämta UID och GID
        uid = int(subprocess.check_output(['id', '-u', username]).strip())
        gid = int(subprocess.check_output(['id', '-g', username]).strip())
        return uid, gid
    except subprocess.CalledProcessError as e:
        print(f"Fel vid hämtning av UID/GID för {username}: {e}")
        sys.exit(1)

def create_home_directory(home_directory, username):
    full_path = os.path.join(home_directory, username)
    try:
        # Skapa katalogen
        os.makedirs(full_path, exist_ok=True)
        print(f"Hemkatalog {full_path} skapad.")

        # Hämta UID och GID för användaren
        uid, gid = get_user_ids(username)

        # Sätt ägare och rättigheter med UID:GID
        subprocess.run(['chown', '-R', f'{uid}:{gid}', full_path], check=True)
        print(f"Ägare och rättigheter satt för {full_path} med UID:GID {uid}:{gid}.")
    except Exception as e:
        print(f"Fel vid skapande av hemkatalog {full_path}: {e}")
        sys.exit(1)



def add_user_to_ldap(username, password, home_directory):
    print(f"Lägger till användare {username} i LDAP...")

    try:
        # Skapa användarpost i LDAP
        subprocess.run([
            'ldapadduser', username, 'users'
        ], check=True)
        print(f"Användare {username} tillagd i LDAP.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid skapande av användare {username} i LDAP: {e}")
        sys.exit(1)

    try:
        # Sätt lösenord
        password_input = f"{password}\n{password}\n"
        subprocess.run(['ldapsetpasswd', username], input=password_input, text=True, check=True)
        print(f"Lösenord för användare {username} satt i LDAP.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid sättande av lösenord för {username}: {e}")
        sys.exit(1)

    try:
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
        # Lägg till -x (enkel bindning), -D (admin-DN) och -w (lösenord)
        subprocess.run([
            'ldapadd',
            '-x',
            '-D', 'cn=admin,dc=grupp13,dc=liu,dc=se',  # Admin-DN
            '-w', 'mIssAn04'                       # Admin-lösenord
        ], input=ldif_content, text=True, check=True)
        print(f"Automount-poster för {username} uppdaterad.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid uppdatering av automount för {username}: {e}")
        sys.exit(1)

    # Skapa hemkatalogen lokalt
    create_home_directory(home_directory, username)

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
