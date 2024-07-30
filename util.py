import platform, os, subprocess, random, string, logging, sys, json, fileinput
import urllib.request as urllib2

logger = logging.getLogger()

string_pool = string.ascii_letters + string.digits
gen_random_text = lambda s: ''.join(map(lambda _: random.choice(string_pool), range(s)))

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.debug(result.stdout.decode())
    if result.returncode != 0:
        logger.debug(result.stderr.decode())
    return result.returncode == 0

def check_os():
    version = platform.version()
    if 'Ubuntu 24.04' not in version:
        logger.debug('OS: ' + version)
        return False
    return True

def not_sudo():
    return os.getuid() != 0

def install_packages():
    logger.debug('Update package lists')
    if not run_command("apt-get update"):
        return False

    logger.debug('Update packages')
    if not run_command("apt-get -y upgrade"):
        return False

    logger.debug('Install node.js')
    if not run_command("apt-get install -y nodejs npm build-essential libssl-dev"):
        return False

    logger.debug('Install vnstat')
    if not run_command("apt-get install -y vnstat vnstati"):
        return False

    logger.debug('Install VPN server packages')
    if not run_command("DEBIAN_FRONTEND=noninteractive apt-get install -q -y strongswan xl2tpd ppp lsof"):
        return False

    return True

def setup_sysctl():
    if not run_command("sh files/sysctl.sh"):
        return False
    return True

def setup_passwords():
    try:
        f = open('/etc/ppp/chap-secrets', 'w')
        pw1 = gen_random_text(12)
        pw2 = gen_random_text(12)
        f.write("username1 l2tpd {} *\n".format(pw1))
        f.write("username2 l2tpd {} *".format(pw2))
        f.close()
        f = open('/etc/ipsec.secrets', 'w')
        f.write('1.2.3.4 %any: PSK "{}"'.format(gen_random_text(16)))
        f.close()
    except Exception as e:
        logger.exception("Exception creating passwords: %s", str(e))
        return False

    return True

def cp_configs():
    logger.debug('xl2tpd.conf')
    if not run_command("cp files/xl2tpd.conf /etc/xl2tpd/xl2tpd.conf"):
        return False

    logger.debug('options.xl2tpd')
    if not run_command("cp files/options.xl2tpd /etc/ppp/options.xl2tpd"):
        return False

    logger.debug('ipsec.conf.template')
    if not run_command("cp files/ipsec.conf.template /etc/ipsec.conf.template"):
        return False

    return True

def setup_vpn():
    logger.debug('Write setup-vpn.sh to /etc')
    if not run_command("cp files/setup-vpn.sh /etc/setup-vpn.sh"):
        return False

    logger.debug('Add to rc.local')
    try:
        with open("/etc/rc.local", "w") as rc_local:
            rc_local.write("#!/bin/sh -e\nbash /etc/setup-vpn.sh\nexit 0\n")
        run_command("chmod +x /etc/rc.local")
    except Exception as e:
        logger.exception("Exception setting up vpn: %s", str(e))
        return False

    logger.debug('Execute setup-vpn.sh')
    if not run_command("bash /etc/setup-vpn.sh"):
        return False

    logger.debug('Ufw default forward policy')

    try:
        for line in fileinput.input("/etc/default/ufw", inplace=True):
            print(line.replace('DEFAULT_FORWARD_POLICY="DROP"', 'DEFAULT_FORWARD_POLICY="ACCEPT"'), end='')
        run_command("service ufw restart")
    except OSError as e:
        logger.warning('ufw not found')

    logger.debug('Copy CLI')
    if not run_command("chmod +x files/instavpn && cp files/instavpn /usr/bin/instavpn"):
        return False

    return True

CRONTAB = '(crontab -l 2>/dev/null; echo "* * * * * vnstati -s -i eth0 -o /opt/instavpn/public/images/vnstat.png") | crontab -'

def webui():
    logger.debug('Generate random password')
    with open('web/server/credentials.json', 'w') as f:
        json.dump({
            "admin": {
                "login": "admin",
                "password": gen_random_text(16)
            }
        }, f)

    logger.debug('Copy web UI directory')
    if not run_command("mkdir --mode=755 -p /opt"):
        return False

    if not run_command("cp -rf web/ /opt/instavpn"):
        return False

    logger.debug('Install node_modules')
    if not run_command("cd /opt/instavpn && npm install"):
        return False

    logger.debug('Copy systemd service script')
    if not run_command("cp files/instavpn.service /etc/systemd/system"):
        return False

    logger.debug('Add vnstati to cron')
    if not run_command(CRONTAB):
        return False

    logger.debug('Start service')
    if not run_command("systemctl daemon-reload && systemctl start instavpn && systemctl enable instavpn"):
        return False

    return True

def info():
    logger.info('')

    with open('/opt/instavpn/server/credentials.json') as f:
        json_data = json.load(f)
        external_ip = urllib2.urlopen("http://api.ipify.org").read().decode()
        logger.info('Browse web UI at http://' + external_ip + ':8080/')
        logger.info("  Username: {}".format(json_data["admin"]["login"]))
        logger.info("  Password: {}".format(json_data["admin"]["password"]))

    logger.info("Completed. Run 'instavpn -h' for help")

if __name__ == "__main__":
    if not check_os():
        sys.exit("This script is intended for Ubuntu 24.04.")

    if not_sudo():
        sys.exit("This script must be run as root.")

    if not install_packages():
        sys.exit("Failed to install required packages.")

    if not setup_sysctl():
        sys.exit("Failed to set up sysctl.")

    if not setup_passwords():
        sys.exit("Failed to set up passwords.")

    if not cp_configs():
        sys.exit("Failed to copy configuration files.")

    if not setup_vpn():
        sys.exit("Failed to set up VPN.")

    if not webui():
        sys.exit("Failed to set up web UI.")

    info()
