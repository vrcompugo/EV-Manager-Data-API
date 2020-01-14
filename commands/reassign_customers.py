from app import db
from app.models import Customer, Lead
from app.modules.importer.sources.bitrix24._association import find_association
from app.modules.importer.sources.bitrix24._connector import post


def reassign_customers():
    customers = db.session.query(Customer).filter(Customer.reseller_id.is_(None)).all()
    total = len(customers)
    printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
    i = 0
    for customer in customers:
        lead = Lead.query.filter(Lead.customer_id == customer.id).first()
        if lead is not None and lead.reseller_id is not None and lead.reseller_id > 0:
            customer.reseller_id = lead.reseller_id
            db.session.commit()
            customer_link = find_association("Customer", local_id=customer.id)
            reseller_link = find_association("Reseller", local_id=customer.reseller_id)
            if customer_link is not None and reseller_link is not None:
                data = {
                    "ID": customer_link.remote_id,
                    "fields[ASSIGNED_BY_ID]": reseller_link.remote_id
                }
                response = post("crm.contact.update", post_data=post_data)
                print(response)

        printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
        i = i + 1
        if i > 1:
            return


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()
