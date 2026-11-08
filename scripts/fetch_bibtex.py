import re, time, json, urllib.request, sys
DOIS = """federici2023zt 10.3390/electronics12030566
zanasi2024flexzt 10.1016/j.adhoc.2024.103414
zhang2026lztaka 10.3390/app16136765
faraj2025provslr 10.1145/3718735
sigwart2019bcprov 10.1145/3365871.3365886
kovach2024sovereign 10.1145/3685651.3686658
asad2026replaypdm 10.3390/systems14101255
lezzi2025cyberres 10.1007/s11301-025-00495-8
alotaibi2026resilient 10.3390/app16042079
rodigari2021ztmc 10.1109/CLOUD53861.2021.00097
alayed2026iztsdn 10.3390/electronics15112376
buccafurri2024mqtti 10.1109/TDSC.2024.3358630
nawab2021wedgechain 10.1109/ICDE51399.2021.00042
saito2025authenticity 10.1109/R10-HTC63995.2025.11394180
tsai2026actuation 10.3390/s26196262
dahlmanns2021entrust 10.1145/3445969.3450423
lazzaro2024mqtt 10.3390/fi16070246
hasan2009tos 10.1145/1629080.1629082
aman2017provenance 10.1145/3055245.3055255
aman2019provenance 10.1109/JIOT.2019.2939286
javaid2018blockpro 10.1145/3282278.3282281
lim2010trust 10.1145/1858158.1858162
rizzardi2016aups 10.1016/j.is.2016.05.004
gigli2025zonia 10.1109/JIOT.2025.3591301
james2025mqttzt 10.1109/CSR64739.2025.11130016
sukumaran2026provenance 10.3390/info17050499
matias2026resilient 10.5753/wtf.2026.24074
yang2018lorawan 10.1109/IoTDI.2018.00022
wang2021kafka 10.1145/3448016.3457556
bu2021opcua 10.1088/1742-6596/1738/1/012119
palyvos2019genealog 10.1016/j.parco.2019.102552
akidau2015dataflow 10.14778/2824032.2824076
shapiro2011crdt 10.1007/978-3-642-24550-3_29
merkle1988signature 10.1007/3-540-48184-2_32
bernstein2012ed25519 10.1007/s13389-012-0027-1
nist_sp800_207 10.6028/NIST.SP.800-207
nist_csf2 10.6028/NIST.CSWP.29
nist_sp800_82r3 10.6028/NIST.SP.800-82r3
nistir_8259a 10.6028/NIST.IR.8259A
din_spec_91345 10.31030/2436156
rfc8032 10.17487/RFC8032
rfc8785 10.17487/RFC8785
rfc9162 10.17487/RFC9162
rfc4303 10.17487/RFC4303
rfc9334 10.17487/RFC9334
rfc5280 10.17487/RFC5280
rfc9846 10.17487/RFC9846"""
out = {}
for line in DOIS.splitlines():
    key, doi = line.split()
    for attempt in range(6):
        try:
            req = urllib.request.Request(f"https://doi.org/{doi}", headers={"Accept": "application/x-bibtex", "User-Agent": "pbti-bib/1.0"})
            b = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace").strip()
            if not b.startswith("@"):
                raise ValueError("not bibtex: " + b[:80])
            b = re.sub(r"^@(\w+)\{[^,]+,", lambda m: "@" + m.group(1) + "{" + key + ",", b, count=1)
            out[key] = b
            print("ok", key, flush=True)
            break
        except Exception as e:
            print("retry", key, e, file=sys.stderr, flush=True)
            time.sleep(3 * (attempt + 1))
    else:
        print("FAILED", key, flush=True)
    time.sleep(0.6)
json.dump(out, open("/home/claude/work/bib/fetched.json", "w"), indent=1)
