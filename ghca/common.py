# Import modules
from datetime import datetime, timedelta

def print_header(str_out):
    """
    Used for styling console header output.
    :param str str_out: (required)
    :return None
    """

    rule = '*' * 120
    print('\n' + rule)
    print('|| %s' % str_out)
    print(rule)
    return None


def print_status(str_status, str_out):
    """
    Prints an output message formatted specifically for status events.
    """
    # '%Y-%m-%d %H:%M:%S'
    str_timestamp = datetime.now().strftime('%H:%M:%S')

    if str_status == 'WARN' or str_status == 'FAIL':
        print('[%s]!(%s): %s' % (str_status, str_timestamp, str_out))
    else:
        print('[%s] (%s): %s' % (str_status, str_timestamp, str_out))


def array_to_md_table(array):
    """
    Converts an array to markdown table, returns the string.
    """

    str_out = ''

    # Iterate over each element
    for row_idx, row in enumerate(array):

        str_out += '\n|'

        # Append the separator to indicate previous was the header
        if row_idx == 1:

            for _ in row:
                str_out += '---|'

            str_out += '\n|'

        for cell in row:
            str_out += cell + '|'

    return str_out

def validate_csv(input_str, delimiter=','):
    """
    Takes a string (CSV formatted) and validates it. Returns the CSV as a string.
    """

    idx = 0
    header_cols = 0
    for row in input_str.splitlines():

        # Get number of columns
        cur_num_cols = len(row.split(delimiter))

        # Load expected number of columns from header
        if idx == 0:
            header_cols = cur_num_cols
        else:
            if header_cols != cur_num_cols:
                print_status('FAIL', 'Number of columns (%d) does not match header (%d).' % (header_cols, cur_num_cols))
                return False

        idx += 1

    # No errors
    return True


def str_datetime_to_utc_offset(str_datetime, int_utc_offset):
    """

    :param str_datetime:
    :param int_utc_offset:
    :return:
    """

    dt_due_date = datetime.strptime(str_datetime, '%Y-%m-%d %H:%M:%S')
    dt_utc = dt_due_date - timedelta(hours=int_utc_offset)

    return dt_utc
