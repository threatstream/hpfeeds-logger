
import json
import traceback
import urlparse
import socket
import hashlib
import re

class ezdict(object):
    def __init__(self, d):
        self.d = d
    def __getattr__(self, name):
        return self.d.get(name, None)

def create_message(event_type, identifier, src_ip, dst_ip, 
    src_port=None, dst_port=None, transport='tcp', protocol='ip', vendor_product=None, 
    direction=None, ids_type=None, severity=None, signature=None, app=None, **kwargs):
    msg = dict(kwargs)
    msg.update({
        'type':   event_type, 
        'sensor': identifier, 
        'src_ip': src_ip,
        'dest_ip': dst_ip,
        'src_port': src_port,
        'dest_port': dst_port,
        'transport': transport,
        'protocol': protocol,
        'vendor_product': vendor_product,
        'direction': direction,
        'ids_type': ids_type,
        'severity': severity,
        'signature': signature,
        'app': app,
    })
    return msg

def glastopf_event(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing glastopf event'
        traceback.print_exc()
        return None 

    if dec.pattern == 'unknown': 
        return None

    return create_message(
        'glastopf.events', 
        identifier, 
        src_ip=dec.source[0], 
        src_port=dec.source[1], 
        dst_ip=None,
        dst_port=80,
        vendor_product='Glastopf',
        app='glastopf',
        direction='inbound',
        ids_type='network',
        severity='high',
        signature='Connection to Honeypot',
    )

def dionaea_capture(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing dionaea event'
        traceback.print_exc()
        return
    return create_message(
        'dionaea.capture', 
        identifier, 
        src_ip=dec.saddr, 
        dst_ip=dec.daddr,
        src_port=dec.sport, 
        dst_port=dec.dport,
        vendor_product='Dionaea',
        app='dionaea',
        direction='inbound',
        ids_type='network',
        severity='high',
        signature='Connection to Honeypot',
        url=dec.url,
        md5=dec.md5,
        sha512=dec.sha512,
    )

def dionaea_connections(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing dionaea connection'
        traceback.print_exc()
        return
    return create_message(
        'dionaea.connections', 
        identifier, 
        src_ip=dec.remote_host, 
        dst_ip=dec.local_host,
        src_port=dec.remote_port, 
        dst_port=dec.local_port,
        vendor_product='Dionaea',
        app='dionaea',
        direction='inbound',
        ids_type='network',
        severity='high',
        signature='Connection to Honeypot',
    )

def beeswarm_hive(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing beeswarm.hive event'
        traceback.print_exc()
        return
    return create_message(
        'beeswarm.hive', 
        identifier, 
        src_ip=dec.attacker_ip, 
        dst_ip=dec.honey_ip,
        src_port=dec.attacker_source_port, 
        dst_port=dec.honey_port,
        vendor_product='Beeswarm',
        app='beeswarm',
        direction='inbound',
        ids_type='network',
        severity='high',
        signature='Connection to Honeypot',
    )

def kippo_sessions(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing kippo event'
        traceback.print_exc()
        return

    messages = []

    base_message = create_message(
        'kippo.sessions', 
        identifier, 
        src_ip=dec.peerIP, 
        dst_ip=dec.hostIP,
        src_port=dec.peerPort, 
        dst_port=dec.hostPort,
        vendor_product='Kippo',
        app='kippo',
        direction='inbound',
        ids_type='network',
        severity='high',
        signature='SSH session on kippo honeypot',
        ssh_version=dec.version
    )

    messages.append(base_message)

    if dec.credentials:
        for username, password in dec.credentials:
            msg = dict(base_message)
            msg['signature'] = 'SSH login attempted on kippo honeypot'
            msg['ssh_username'] = username
            msg['ssh_password'] = password
            messages.append(msg)

    if dec.urls:
        for url in dec.urls:
            msg = dict(base_message)
            msg['signature'] = 'URL download attempted on kippo honeypot'
            msg['url'] = url
            messages.append(msg)

    if dec.commands:
        for command in dec.commands:
            msg = dict(base_message)
            msg['signature'] = 'command attempted on kippo honeypot'
            msg['command'] = command
            messages.append(msg)

    if dec.unknownCommands:
        for command in dec.unknownCommands:
            msg = dict(base_message)
            msg['signature'] = 'unknown command attempted on kippo honeypot'
            msg['command'] = command
            messages.append(msg)

    return messages

def conpot_events(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
        remote = dec.remote[0]
        port = dec.remote[1]

        # http asks locally for snmp with remote ip = "127.0.0.1"
        if remote == "127.0.0.1":
            return
    except:
        print 'exception processing conpot event'
        traceback.print_exc()
        return

    return create_message(
        'conpot.events-'+dec.data_type, 
        identifier, 
        src_ip=remote, 
        dst_ip=dec.public_ip,
        src_port=port,
        dst_port=502,
        vendor_product='Conpot',
        app='conpot',
        direction='inbound',
        ids_type='network',
        severity='medium',
        signature='Connection to Honeypot',

    )

def snort_alerts(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing snort alert'
        traceback.print_exc()
        return None
    return create_message(
        'snort.alerts', 
        identifier, 
        src_ip=dec.source_ip, 
        dst_ip=dec.destination_ip,
        src_port=dec.source_port, 
        dst_port=dec.destination_port,
        transport=dec.protocol,
        vendor_product='Snort',
        app='snort',
        direction='inbound',
        ids_type='network',
        severity='high',
        signature=dec.signature,

        # TODO: pull out the other snort specific items
        # 'snort': {
        #         'header': o_data['header'],
        #         'signature': o_data['signature'],
        #         'classification': o_data['classification'],
        #         'priority': o_data['priority'],
        #     },
        #     'sensor': o_data['sensor'] # UUID
    )

def suricata_events(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing suricata event'
        traceback.print_exc()
        return None
    return create_message(
        'suricata.events', 
        identifier, 
        src_ip=dec.source_ip, 
        dst_ip=dec.destination_ip,
        src_port=dec.source_port, 
        dst_port=dec.destination_port,
        transport=dec.protocol,
        vendor_product='Suricata',
        app='suricata',
        direction='inbound',
        ids_type='network',
        severity='high',
        signature=dec.signature,

        # TODO: add the suricata specific items:
        # 'suricata': {
        #         'action':         o_data['action'],
        #         'signature':      o_data['signature'],
        #         'signature_id':   o_data['signature_id'],
        #         'signature_rev':  o_data['signature_rev'],
        #     },
        #     'sensor': o_data['sensor'] # UUID
    )

def p0f_events(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing suricata event'
        traceback.print_exc()
        return None
    return create_message(
        'p0f.events', 
        identifier, 
        src_ip=dec.client_ip, 
        dst_ip=dec.server_ip,
        src_port=dec.client_port, 
        dst_port=dec.server_port,
        vendor_product='p0f',
        app='p0f',
        direction='inbound',
        ids_type='network',
        severity='informational',
        signature='Packet Observed by p0f',
        p0f_app=dec.app,
        p0f_link=dec.link,
        p0f_os=dec.os,
        p0f_uptime=dec.uptime,
    )

def amun_events(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing amun event'
        traceback.print_exc()
        return
    return create_message(
        'amun.events', 
        identifier, 
        src_ip=dec.attackerIP, 
        dst_ip=dec.victimIP,
        src_port=dec.attackerPort, 
        dst_port=dec.victimPort,
        vendor_product='Amun',
        app='amun',
        direction='inbound',
        ids_type='network',
        severity='high',
        signature='Connection to Honeypot',
    )

def wordpot_event(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing wordpot alert'
        traceback.print_exc()
        return

    return create_message(
        'wordpot.alerts', 
        identifier, 
        src_ip=dec.source_ip, 
        dst_ip=dec.dest_ip,
        src_port=dec.source_port, 
        dst_port=dec.dest_port,
        vendor_product='Wordpot',
        app='wordpot',
        direction='inbound',
        ids_type='network',
        severity='high',
        signature='Wordpress Exploit, Scan, or Enumeration Attempted',
    )

def shockpot_event(identifier, payload):
    try:
        dec = ezdict(json.loads(str(payload)))
    except:
        print 'exception processing shockpot alert'
        traceback.print_exc()
        return None

    kwargs = {}
    if dec.command_data:
        m = hashlib.md5()
        m.update(dec.command_data)
        kwargs['md5'] = m.hexdigest()

        m = hashlib.sha1()
        m.update(dec.command_data)
        kwargs['sha1'] = m.hexdigest()

        m = hashlib.sha256()
        m.update(dec.command_data)
        kwargs['sha256'] = m.hexdigest()

        m = hashlib.sha512()
        m.update(dec.command_data)
        kwargs['sha512'] = m.hexdigest()

    if dec.command:
        m = re.search('(?P<url>https?://[^\s;]+)', dec.command)
        if m:
            kwargs.update(m.groupdict())

    try:
        p = urlparse.urlparse(dec.url)
        host = p.netloc.split(':')[0]
        socket.inet_aton(host)
        dest_ip = host
    except:
        dest_ip = None

    return create_message(
        'shockpot.events', 
        identifier, 
        src_ip=dec.source_ip, 
        dst_ip=dest_ip,
        src_port=0,
        dst_port=dec.dest_port,
        vendor_product='ThreatStream Shockpot',
        app='shockpot',
        direction='inbound',
        ids_type='network',
        severity='high',
        signature='Shellshock Exploit Attempted',
        **kwargs
    )
