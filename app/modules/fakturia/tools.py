import xmltodict
import json


def fix_sepa_files():
    print("fixer")
    files = [
        "SEPA_CORE_2022-07-01_15-26-32_DE84460628175191056500_FSLGU8CSXPLFATBWQ9O1GPINOKJREYHC3VM.xml",
        "SEPA_CORE_2022-07-01_15-28-34_DE84460628175191056500_FSLVQFZ5WQBTU3U1OJ8IZDWRQ3F9PPRJEFH.xml",
        "SEPA_CORE_2022-07-01_15-30-39_DE84460628175191056500_FSLF6WG2U4XUODZ72IXYVEIYPCSLU2DZC5L.xml",
        "SEPA_CORE_2022-07-01_15-32-14_DE84460628175191056500_FSL2HKEBSIKMHYZWEFHTE3OQHIUVDPFGWUX.xml",
        "SEPA_CORE_2022-07-01_15-34-32_DE84460628175191056500_FSLYGZHINEFSV11UMCIKOJNZYDJ5UYNHUUX.xml",
        "SEPA_CORE_2022-07-01_15-36-47_DE84460628175191056500_FSLTYP770D6YOPDSBRQSZ2NTKCGT4WP02NE.xml",
    ]
    transactions = []
    existing_transactions = []
    document = {"CtrlSum": 0}
    for file in files:
        with open(f'app/modules/fakturia/sepa_files/{file}', 'r', encoding='utf-8') as file:
            my_xml = file.read()

        # Use xmltodict to parse and convert
        # the XML document
        my_dict = xmltodict.parse(my_xml)
        items = my_dict.get("Document").get("CstmrDrctDbtInitn").get("PmtInf").get("DrctDbtTxInf")
        for item in items:
            if item.get("RmtInf").get("Ustrd") not in existing_transactions:
                existing_transactions.append(item.get("RmtInf").get("Ustrd"))
                transactions.append(item)
                document["CtrlSum"] = document["CtrlSum"] + float(item.get("InstdAmt").get("#text"))
    print(document["CtrlSum"])

    xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02 pain.008.001.02.xsd">
    <CstmrDrctDbtInitn>
        <GrpHdr>
            <MsgId>FSL2HKEBSIKMHYZWEFHTE3OQHIUVDPFGWUX</MsgId>
            <CreDtTm>2022-07-01T15:32:20</CreDtTm>
            <NbOfTxs>{len(transactions)}</NbOfTxs>
            <CtrlSum>{document["CtrlSum"]}</CtrlSum>
            <InitgPty><Nm>Korbacher Energiezentrum</Nm></InitgPty>
        </GrpHdr>
        <PmtInf>
            <PmtInfId>FSL2HKEBSIKMHYZWEFHTE3OQHIUVDPFGWUX</PmtInfId>
            <PmtMtd>DD</PmtMtd>
            <NbOfTxs>{len(transactions)}</NbOfTxs>
            <CtrlSum>{document["CtrlSum"]}</CtrlSum>
            <PmtTpInf>
                <SvcLvl>
                    <Cd>SEPA</Cd>
                </SvcLvl>
                <LclInstrm><Cd>CORE</Cd></LclInstrm>
                <SeqTp>RCUR</SeqTp>
            </PmtTpInf>
            <ReqdColltnDt>2022-07-11</ReqdColltnDt>
            <Cdtr><Nm>Korbacher Energiezentrum</Nm></Cdtr>
            <CdtrAcct><Id><IBAN>DE84460628175191056500</IBAN></Id></CdtrAcct>
            <CdtrAgt><FinInstnId><BIC>GENODEM1SMA</BIC></FinInstnId></CdtrAgt>
            <ChrgBr>SLEV</ChrgBr>'''
    for transaction in transactions:
        xml = xml + f'''
            <DrctDbtTxInf>
                <PmtId><EndToEndId>{transaction.get('PmtId').get('EndToEndId')}</EndToEndId></PmtId>
                <InstdAmt Ccy="EUR">{transaction.get("InstdAmt").get("#text")}</InstdAmt>
                <DrctDbtTx>
                    <MndtRltdInf>
                        <MndtId>{transaction.get("DrctDbtTx").get("MndtRltdInf").get("MndtId")}</MndtId>
                        <DtOfSgntr>{transaction.get("DrctDbtTx").get("MndtRltdInf").get("DtOfSgntr")}</DtOfSgntr>
                        <AmdmntInd>{transaction.get("DrctDbtTx").get("MndtRltdInf").get("AmdmntInd")}</AmdmntInd>
                    </MndtRltdInf>
                    <CdtrSchmeId>
                        <Id>
                            <PrvtId>
                                <Othr>
                                    <Id>{transaction["DrctDbtTx"]["CdtrSchmeId"]["Id"]["PrvtId"]["Othr"]["Id"]}</Id>
                                    <SchmeNm>
                                        <Prtry>{transaction["DrctDbtTx"]["CdtrSchmeId"]["Id"]["PrvtId"]["Othr"]["SchmeNm"]["Prtry"]}</Prtry>
                                    </SchmeNm>
                                </Othr>
                            </PrvtId>
                        </Id>
                    </CdtrSchmeId>
                </DrctDbtTx>
                <DbtrAgt>
                    <FinInstnId><BIC>{transaction["DbtrAgt"]["FinInstnId"]["BIC"]}</BIC></FinInstnId>
                </DbtrAgt>
                <Dbtr><Nm>{transaction["Dbtr"]["Nm"]}</Nm></Dbtr>
                <DbtrAcct><Id><IBAN>{transaction["DbtrAcct"]["Id"]["IBAN"]}</IBAN></Id></DbtrAcct>
                <RmtInf><Ustrd>{transaction["RmtInf"]["Ustrd"]}</Ustrd></RmtInf>
            </DrctDbtTxInf>
        '''
    xml = xml + '''</PmtInf></CstmrDrctDbtInitn></Document>'''
    with open(f'app/modules/fakturia/sepa_files/combined.xml', 'w', encoding='utf-8') as file:
        file.write(xml)
