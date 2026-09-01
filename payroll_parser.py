"""
    This script downloads pay statements from a secure online portal using a supplied login cookie.
    It then parses the earning and deductions from their JSON format and creates an output file
    formatting pay information by date in a manner that can be used by an online accounting software.
"""

import json
import requests
import os


def extract_statement_links(statement_list_content: dict) -> list[str]:
    """
    :param statement_list_content: json statement list downloaded from https://my.adp.com/v1_0/O/A/payStatements?adjustments=yes&numberoflastpaydates=300
    :return: list of statement links like "https://my.adp.com/v1_0/O/A/payStatement/0755275526063334305611002799859"
    """
    links = [st['payDetailUri']['href'] for st in statement_list_content['payStatements']]
    return ['https://my.adp.com' + link for link in links]


def download_statement(link: str) -> dict:
    """
    Takes a statement link as input and creates a file with the corresponding statement information.
    :param link: statement link string
    :return: a dictionary with pay statement information
    """

    new_fn = link.split('/')[-1] + ".json"

    #check if file exists
    if os.path.exists(new_fn):
        data = json.load(open(new_fn))
        return data

    # download from link
    with open('scratch.txt', 'r') as cookie:
        response = requests.get(link, headers={'Cookie': cookie.readline()})
        response.raise_for_status()
        try:
            statement_data = response.json()
        except Exception:
            print("Failed to parse JSON")
            print("Status:", response.status_code)
            print("Response:", response.text[:500])
        with open(new_fn, 'w') as output:
            json.dump(statement_data, output)

        # return filename
        return statement_data


def extract_earnings(statement: dict) -> list[tuple]:
    """
    Parses positive gains out of pay statements.
    :param statement: pay statement dictionary
    :return: list of incomes
    """

    earnings = statement['payStatement']['earnings']
    earning_list = []

    for earning in earnings:

        if 'earningCodeName' in earning:
            code = earning['earningCodeName']
        else:
            code = None
        if 'earningAmount' in earning and 'amountValue' in earning['earningAmount']:
            amount = earning['earningAmount']['amountValue']
        else:
            amount = None
        if 'preTaxIndicator' in earning:
            tax_ind = earning['preTaxIndicator']
        else:
            tax_ind = None
        earning_list.append((code, amount, tax_ind))

    return earning_list


def extract_deductions(statement: dict) -> list[tuple]:
    """
    Parses deductions from pay statements.
    :param statement: pay statement dictionary
    :return: list of deductions
    """
    deductions = statement['payStatement']['deductions']

    deduction_list = []

    for deduction in deductions:

        if 'CodeName' in deduction:
            code = deduction['CodeName']
        else:
            code = None
        if 'deductionAmount' in deduction and 'amountValue' in deduction['deductionAmount']:
            amount = deduction['deductionAmount']['amountValue']
        else:
            amount = None
        deduction_list.append((code, amount))

    return deduction_list


def write_2file(date, earnings, deductions, filename="finance_tracker.txt") -> None:
    """
    Writes a file outlining all gains and losses categorized by type/tax code. Formats the
    file in a way that can be read by an online financial service platform.

        # for each statement, write the statement in this format
        # yyyy-mm-dd * "some comment - maybe statement date?"
        #     Assets:US:BECU:Savings9646 +1234.56     <-- repeat this line for every bit of income (positive $ value in statement)https://code-with-me.global.jetbrains.com/ScLoKmcRT7mN_HZp-ZLVNg#p=PY&fp=F1F6D92E4485F99A09191263C2919F113E663685157BCB0AA750B3A619812AD8&newUi=true
        #     Expenses:Taxes:US:TY20XX:<category> -123.45   <-- repeat this line once for every deduction (negative $ value in statement)

        # format reference/example:  https://beancount.github.io/docs/command_line_accounting_cookbook.html#booking-salary-deposits
    :param date: statement date
    :param earnings: list of earnings
    :param deductions: list of deductions
    :param filename: output file name
    :return: None
    """

    with open(filename, 'a', encoding='utf-8') as file:

        # write the date of the statement
        date_line = date + " * " + '"Paycheck"'
        file.write(date_line + "\n")

        for earning in earnings:   # format (code, amount, tax_ind)
            if earning[1] == None:
                continue
            asset_line = "  Assets:US:BECU:Savings9638 " + "+" + str(earning[1]) + " USD"
            file.write(asset_line + "\n")

        for deduction in deductions:   # format (code, amount)
            if deduction[1] == None:
                continue
            # look up deduction code in dictionary
            if deduction[0] in CODE_NAME_TO_CATEGORY:
                codename = CODE_NAME_TO_CATEGORY[deduction[0]]
            else:
                codename = deduction[0]
            expenses_line = "  Expenses:" + codename + " " + str(deduction[1]) + " USD"
            file.write(expenses_line + "\n")



def read_json_file(f):
    with open(f, 'r') as file:
        return json.load(file)


def main() -> None:

    statement_list_content = read_json_file('statement_list.json')
    # extract all links
    statement_links = extract_statement_links(statement_list_content)

    if os.path.exists('finance_tracker.txt'):
        os.unlink('finance_tracker.txt')

    for link in statement_links:
        print(f"Processing {link}")
        # download statement and read data
        raw_statement = download_statement(link)
        print(f"Downloaded (or using existing file)")
        # get statement date
        date = raw_statement['payStatement']['payDate']
        print(f"Read statement for {date}")
        # get earnings
        earnings = extract_earnings(raw_statement)
        print(f"Read {len(earnings)} earnings")
        # get deductions
        deductions = extract_deductions(raw_statement)
        print(f"Read {len(deductions)} deductions")
        # write to file
        write_2file(date, earnings, deductions)
        print(f"Wrote content")

    pass

CODE_NAME_TO_CATEGORY = {
"Aetna Medical             ": "Medical",
"Banking": "Banking",
"Benefits": "Benefits",
"Dental                    ": "Dental",
"ESPP 2                    ": "ESPP",
"Ee Sup Life Ins           ": "LifeInsurance",
"Federal Income Tax        ": "Federal",
"Holiday        ": "Holiday",
"Long Term Care            ": "LongTermCare",
"Medicare Tax              ": "Medicare",
"Other": "Other",
"Regular        ": "Regular",
"Retirement": "Retirement",
"Roth $                    ": "Roth",
"Savings 2                 ": "Savings9648",
"Social Security Tax       ": "SocialSecurity",
"Spark Award    ": "Spark",
"Spark Offset              ": "SparkOffset",
"Taxes": "Taxes",
"Vision                    ": "Vision",
"WA Paid Family Leave Ins  ": "WAPFML",
"WA Paid Medical Leave Ins ": "WAPFML",
"Wellness Prog  ": "Wellness",
}

if __name__ == '__main__':
    main()