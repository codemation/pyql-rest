from pyql import data
import os, unittest, json, time


class TestData(unittest.TestCase):
    def test_run_mysql_test(self):
        import mysql.connector
        os.environ['DB_USER'] = 'josh'
        os.environ['DB_PASSWORD'] = 'abcd1234'
        os.environ['DB_HOST'] = 'localhost' if not 'DB_HOST' in os.environ else os.environ['DB_HOST']
        os.environ['DB_PORT'] = '3306'
        os.environ['DB_NAME'] = 'joshdb'
        os.environ['DB_TYPE'] = 'mysql'

        env = ['DB_USER','DB_PASSWORD','DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_TYPE']
        conf = ['user','password','host','port', 'database', 'type']
        config = {CONF_VAR: os.getenv(DB_VAR).rstrip() for DB_VAR, CONF_VAR in zip(env,conf)}

        db = data.Database(
            mysql.connector.connect, 
            **config
            )
        test(db)
    def test_run_sqlite_test(self):
        import sqlite3
        db = data.Database(
            sqlite3.connect, 
            database="testdb"
            )
        test(db)
        ref_db = data.Database(
            sqlite3.connect, 
            database="testdb"
            )
        print(ref_db.tables)
        col_names = ['order_num', 'date', 'trans', 'symbol', 'qty', 'price', 'after_hours']
        for col in col_names:
            assert col in ref_db.tables['stocks'].columns, f"missing column {col}"
    
def test(db):
    import random
    def check_sel(requested, selection):
        request_items = []
        if requested == '*':
            request_items = trade.keys()
        else:
            for request in requested:
                assert request in trade, f'{request} is not a valid column in {trade}'
                request_items.append(request)
        
        for col, value in trade.items():
            if col in request_items:
                assert len(selection) > 0, f"selection should be greater than lenth 0, data was inserted"
                assert col in selection[0], f"missing column '{col}' in select return"
                assert str(value) == str(sel[0][col]), f"value {selection[0][col]} returned from select is not what was inserted {value}."


    assert 'data.Database' in str(type(db)), f"failed to create data.Database object) - {str(type(db))} instead"
    db.run('drop table stocks')
    db.create_table(
        'stocks', 
        [    
            ('order_num', int, 'AUTO_INCREMENT' if db.type == 'mysql' else 'AUTOINCREMENT'),
            ('date', str),
            ('trans', str),
            ('symbol', str),
            ('qty', int),
            ('price', float),
            ('after_hours', bool)
        ], 
        'order_num' # Primary Key 
    )
    print(db.tables['stocks'].columns)
    assert 'stocks' in db.tables, "table creation failed"


    db.run('drop table employees')
    db.run('drop table positions')
    db.run('drop table departments')
    db.create_table(
        'departments', 
        [    
            ('id', int, 'UNIQUE'),
            ('name', str)

        ], 
        'id' # Primary Key 
    )
    assert 'departments' in db.tables, "table creation failed"

    db.create_table(
        'positions', 
        [    
            ('id', int, 'UNIQUE'),
            ('name', str),
            ('department_id', int)

        ], 
        'id', # Primary Key
        foreign_keys={
            'department_id': {
                    'table': 'departments', 
                    'ref': 'id',
                    'mods': 'ON UPDATE CASCADE ON DELETE CASCADE'
            }
        }
    )
    assert 'positions' in db.tables, "table creation failed"

    db.create_table(
        'employees', 
        [    
            ('id', int, 'UNIQUE'),
            ('name', str),
            ('position_id', int),

        ], 
        'id', # Primary Key
        foreign_keys={
            'position_id': {
                    'table': 'positions', 
                    'ref': 'id',
                    'mods': 'ON UPDATE CASCADE ON DELETE CASCADE'
            }
        }
    )
    assert 'employees' in db.tables, "table creation failed"


    db.run('drop table keystore')
    db.create_table(
        'keystore', 
        [    
            ('env', str, 'UNIQUE NOT NULL'),
            ('val', str)
        ], 
        'env' # Primary Key 
    )

    assert 'keystore' in db.tables, "table creation failed"

    ##

    # key - value col insertion using tb[keyCol] = valCol
    db.tables['keystore']['key1'] = 'value1'
    assert 'key1' in db.tables['keystore'], "insertion failed using setitem"
    assert db.tables['keystore']['key1'] == 'value1', "value retrieval failed for key-value table"

    # key - value col update using setitem
    db.tables['keystore']['key1'] = 'newValue1'
    assert db.tables['keystore']['key1'] == 'newValue1', "update failed using setitem"

    # double col insertion using json

    db.tables['keystore']['config1'] = {'a': 1, 'b': 2, 'c': 3}
    assert 'config1' in  db.tables['keystore'], "insertion failed using setitem for json data"

    col_names = ['order_num', 'date', 'trans', 'symbol', 'qty', 'price', 'after_hours']
    for col in col_names:
        assert col in db.tables['stocks'].columns

    # JSON Load test
    tx_data = {'type': 'BUY', 'condition': {'limit': '36.00', 'time': 'EndOfTradingDay'}}

    trade = {'order_num': 1, 'date': '2006-01-05', 'trans': tx_data, 'symbol': 'RHAT', 'qty': 100, 'price': 35.14, 'after_hours': True}

    # pre insert * select # trade
    sel = db.tables['stocks'].select('*')
    assert not len(sel) > 0, "no values should exist yet"


    db.tables['stocks'].insert(**trade)
    #    OR
    # db.tables['stocks'].insert(
    #     date='2006-01-05', # Note order_num was not required as auto_increment was specified
    #     trans='BUY',
    #     symbol='NTAP',
    #     qty=100.0,
    #     price=35.14,
    #     after_hours=True
    # )
    import uuid
    # create departments
    departments = [
        {'id': 1001, 'name': 'HR'},
        {'id': 2001, 'name': 'Sales'},
        {'id': 3001, 'name': 'Support'},
        {'id': 4001, 'name': 'Marketing'}
    ]
    for department in departments:
        db.tables['departments'].insert(**department)
    
    positions = [
        {'id': 100101, 'name': 'Director', 'department_id': 1001},
        {'id': 100102, 'name': 'Manager', 'department_id': 1001},
        {'id': 100103, 'name': 'Rep', 'department_id': 1001},
        {'id': 100104, 'name': 'Intern', 'department_id': 1001},
        {'id': 200101, 'name': 'Director', 'department_id': 2001},
        {'id': 200102, 'name': 'Manager', 'department_id': 2001},
        {'id': 200103, 'name': 'Rep', 'department_id': 2001},
        {'id': 200104, 'name': 'Intern', 'department_id': 2001},
        {'id': 300101, 'name': 'Director', 'department_id': 3001},
        {'id': 300102, 'name': 'Manager', 'department_id': 3001},
        {'id': 300103, 'name': 'Rep', 'department_id': 3001},
        {'id': 300104, 'name': 'Intern', 'department_id': 3001},
        {'id': 400101, 'name': 'Director', 'department_id': 4001},
        {'id': 400102, 'name': 'Manager', 'department_id': 4001},
        {'id': 400103, 'name': 'Rep', 'department_id': 4001},
        {'id': 400104, 'name': 'Intern', 'department_id': 4001}
    ]
    
    def get_random_name():
        name = ''
        first_names = ['Jane', 'Jill', 'Joe', 'John', 'Chris', 'Clara', 'Dale', 'Dana', 'Eli', 'Elly', 'Frank', 'George']
        last_names = ['Adams', 'Bale', 'Carson', 'Doe', 'Franklin','Smith', 'Wallace', 'Jacobs']
        random_first, random_last = random.randrange(len(first_names)-1), random.randrange(len(last_names)-1)
        return f"{first_names[random_first]} {last_names[random_last]}"
    employees = []
    def add_employee(employee_id, count, position_id):
        emp_id = employee_id
        for _ in range(count):
            employees.append({'id': emp_id, 'name': get_random_name(), 'position_id': position_id})
            emp_id+=1
    employee_id = 1000
    for position in positions:
        print(position)
        db.tables['positions'].insert(**position)
        if position['name'] == 'Director':
            add_employee(employee_id, 1, position['id'])
            employee_id+=1
        elif position['name'] == 'Manager':
            add_employee(employee_id, 2, position['id'])
            employee_id+=2
        elif position['name'] == 'Rep':
            add_employee(employee_id, 4, position['id'])
            employee_id+=4
        else:
            add_employee(employee_id, 8, position['id'])
            employee_id+=8

    
    for employee in employees:
        db.tables['employees'].insert(**employee)
    # Select Data

    # join selects

    for position, count in [('Director', 4), ('Manager', 8), ('Rep', 16), ('Intern', 32)]:
        join_sel = db.tables['employees'].select(
            '*', 
            join={
                'positions': {'employees.position_id': 'positions.id'},
                'departments': {'positions.department_id': 'departments.id'}
                },
            where={
                'positions.name': position
                }
            )
        assert len(join_sel) == count, f"expected number of {position}'s' is {count}, found {len(join_sel)}"
    for department in ['HR', 'Marketing', 'Support', 'Sales']:
        for position, count in [('Director', 1),('Manager', 2), ('Rep', 4), ('Intern', 8)]:
            join_sel = db.tables['employees'].select(
                '*', 
                join={
                    'positions': {'employees.position_id': 'positions.id'},
                    'departments': {'positions.department_id': 'departments.id'}
                    },
                where={
                    'positions.name': position,
                    'departments.name': department
                    }
                )
            assert len(join_sel) == count, f"expected number of {position}'s' is {count}, found {len(join_sel)}"

    # join select - testing default key usage if not provided
    for position, count in [('Director', 4),('Manager', 8), ('Rep', 16), ('Intern', 32)]:
        join_sel = db.tables['employees'].select(
            '*', 
            join='positions',
            where={'positions.name': position}
            )
        assert len(join_sel) == count, f"expected number of {position}'s' is {count}, found {len(join_sel)}"

    # join select - testing multiple single table conditions
    join_sel = db.tables['employees'].select(
            '*', 
            join={
                'positions': {
                            'employees.position_id':'positions.id', 
                            'positions.id': 'employees.position_id'
                            }
                }
    )
    assert len(join_sel) == 60, f"expected number of employee's' is {60}, found {len(join_sel)}"

    
    # * select #
    sel = db.tables['stocks'].select('*')
    print(sel)
    check_sel('*', sel)

    try:
        sel = db.tables['stocks'].select('*', where={'doesNotExist': 'doesNotExist'})
    except Exception as e:
        assert type(e) == data.InvalidInputError, "select should have resulted in exception"

    # Iter Check
    sel = [row for row in db.tables['stocks']]
    check_sel('*', sel)
    print(f"iter check ")

    # Partial insert

    partial_trade = {'date': '2006-01-05', 'trans': tx_data, 'price': 35.16,'qty': None, 'after_hours': True}

    db.tables['stocks'].insert(**partial_trade)

    # * select # 
    sel = db.tables['stocks'].select('*')
    print(sel)
    check_sel('*', sel)

    # * select NULL check # 
    sel = db.tables['stocks'].select('*', where={'qty': None})
    print(sel)
    assert len(sel) > 0, "we should find at least 1 row with a NULL qty" 
    
    # * select + where # 
    sel = db.tables['stocks'].select('*', where={'symbol':'RHAT'})
    print(sel)
    check_sel('*', sel)

    # single select 
    sel = db.tables['stocks'].select('price', where={'symbol':'RHAT'})
    check_sel(['price'], sel)
    print(sel)
    # multi-select 
    sel = db.tables['stocks'].select('price', 'date', where={'symbol':'RHAT'})
    check_sel(['price', 'date'], sel)
    print(sel)
    
    # Update Data
    tx_old = {'type': 'BUY', 'condition': {'limit': '36.00', 'time': 'EndOfTradingDay'}}
    tx_data['type'] = 'SELL'
    
    db.tables['stocks'].update(
        symbol='NTAP',trans=tx_data,
        after_hours=False, qty=101, 
        where={'order_num': 1, 'after_hours': True, 'trans': tx_old})
    sel = db.tables['stocks'].select('*', where={'order_num': 1})[0]
    print(sel)
    assert sel['trans']['type'] == 'SELL' and sel['symbol'] == 'NTAP', f"values not correctly updated"


    # Update Data via setItem
    db.tables['stocks'][1] = {'symbol': 'NTNX', 'trans': {'type': 'BUY'}}
    # Select via getItem
    sel = db.tables['stocks'][1]
    print(sel)
    assert sel['trans']['type'] == 'BUY' and sel['symbol'] == 'NTNX', f"values not correctly updated"


    # update data - use None Value
    db.tables['stocks'].update(
        symbol=None,trans=tx_data,
        after_hours=False, qty=101, 
        where={'qty': 101})

    # * select NULL check # 
    sel = db.tables['stocks'].select('*', where={'qty': 101, 'symbol': None})
    print(sel)
    assert len(sel) > 0, "we should find at least 1 row with a NULL symbol" 

    # Check 'in' functioning
    assert 1 in db.tables['stocks'], "order 1 should still exist"
    print(sel)

    # Delete Data 

    db.tables['stocks'].delete(where={'order_num': 1, 'after_hours': False})
    sel = db.tables['stocks'].select('*', where={'order_num': 1, 'after_hours': False})
    print(sel)
    assert len(sel) < 1, "delete should have removed order_num 1"

    # Check 'in' functioning
    assert not 1 in db.tables['stocks'], "order 1 should not still exist"

    # Check 'in' functioning for db

    assert 'stocks' in db, "stocks table should still exist here"

if __name__ == '__main__':
    import sys
    """
        os.environ['DB_USER'] = 'josh'
        os.environ['DB_PASSWORD'] = 'abcd1234'
        os.environ['DB_HOST'] = 'localhost' if not 'DB_HOST' in os.environ else os.environ['DB_HOST']
        os.environ['DB_PORT'] = '3306'
        os.environ['DB_NAME'] = 'joshdb'
        os.environ['DB_TYPE'] = 'mysql'
    """
    db = {}
    print(f"{len(sys.argv)} - {sys.argv}")
    db['DB_HOST'], db['DB_PORT'], db['DB_NAME'], db['DB_TYPE'], db['DB_USER'], db['DB_PASSWORD'] = sys.argv[1:]
    for arg, v in db.items():
        os.environ[arg] = v
    env = ['DB_USER','DB_PASSWORD','DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_TYPE']
    conf = ['user','password','host','port', 'database', 'type']
    config = {CONF_VAR: os.getenv(DB_VAR).rstrip() for DB_VAR, CONF_VAR in zip(env,conf)}
    import mysql.connector
    MAX_DB_CONNECT_RETRY = 3
    try_count = 1
    while try_count <= MAX_DB_CONNECT_RETRY:
        try:
            db = data.Database(mysql.connector.connect, **config)
            break
        except Exception as e:
            print(f"exception setting up db object - {repr(e)} - will retry {try_count} after 10 sec")
        time.sleep(10)
        try_count+=1
    test(db)