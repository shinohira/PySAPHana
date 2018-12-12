import pyhdb
from pyhdb.exceptions import OperationalError
from flask import Flask, render_template, request, current_app, g, flash
import flask_excel as excel

app = Flask(__name__)
app.config.from_object('config.RDQConfig')
excel.init_excel(app)

@app.route('/', methods=('GET', 'POST'))
def home():
    # ---------- GET Request ----------#
    if request.method == 'GET':
        return render_template('index.html', title='Build your query', schema='SAPABAP1')
    
    # ---------- POST Request ----------#
    mode = request.form.get('action')
    schema = request.form.get('schema').upper()
    table = request.form.get('table').upper()
    limit = where = columns = ''
    thead = []

    pyhdb_conn = pyhdb.connect(
        host=current_app.config['DATABASE'],
        port=current_app.config['PORT'],
        user=current_app.config['USER'],
        password=current_app.config['PASSWORD']
    )
    g.db = pyhdb_conn
    
    if mode == 'getcol':
    # ---------- Build SQL for metadata to display Column Names ----------#
        sql = "select A.POSITION, A.COLUMN_NAME, B.DDTEXT, A.DATA_TYPE_NAME from "\
                + "(select TABLE_NAME, COLUMN_NAME, POSITION, DATA_TYPE_NAME from "\
                + "SYS.TABLE_COLUMNS where SCHEMA_NAME = '" + schema + "' and TABLE_NAME = '" + table + "') as A "\
                + "left outer join "\
                + "(select TABNAME, FIELDNAME, DDTEXT from "\
                + "SAPABAP1.DD03M where TABNAME = '" + table + "' and DDLANGUAGE = 'E') as B "\
                + "on A.TABLE_NAME = B.TABNAME and A.COLUMN_NAME = B.FIELDNAME order by A.POSITION"
        limit = 500
        thead = ['Nr.', 'Column', 'Text', 'Type']
    elif mode == 'exec' or mode == 'export':
    # ---------- On execute SQL or excel export ----------#
        selcol = request.form.getlist('selcol')
        limit = request.form.get('limit')
        where = request.form.get('where').upper()
        columns = request.form.get('columns')
        # ---------- Build columns clause for fetch records from a table ----------#
        if not selcol and not columns:
            flash('Select at least one column.', category='label label-rounded label-error')
            return render_template('index.html', title='Build your query', schema=schema, table=table, limit=limit, where=where)
        elif not selcol and columns:
            selcol = [x.strip() for x in columns.split(',')]

        cols = ''
        for col in selcol:
            cols += col + ','
        cols = cols[0:len(cols)-1]
        sql = "select " + cols + " from " + schema + "." + table + " " + where + " limit " + limit

        # ---------- Build parameters for template, columns:textarea, thead:table hedder ----------#
        columns = cols
        thead = selcol

    c = pyhdb_conn.cursor()
    rs = c.execute(sql).fetchall()
    c.close()

    if rs:
        if len(rs) > 5000:
            flash(str(len(rs)) + ' records hit. ' + 'Limit your query up to 5000 rows.', category='label label-rounded label-error')
            rs = None
    else:
        flash('No records found.', category='label label-rounded label-error')
    
    # ---------- Returns Xlsx response ----------#
    if mode == 'export':
        lst = []
        arr = []
        arr.append(thead)
        for row in rs:
            for col in row:
                lst.append(col)
            arr.append(lst)
            lst = []
        return excel.make_response_from_array(arr, 'xlsx', file_name='export')
    
    # ---------- Returns HTTP response ----------#
    return render_template('index.html', title='Result', mode=mode, thead=thead, rs=rs, schema=schema, table=table, limit=limit, columns=columns, where=where)

@app.after_request
def after_request(response):
    if hasattr(g, 'db'):
        if g.db is not None:
            try:
                g.db.close()
            except OperationalError as e:
                print('>>>>>>>>>>>>>>>>> '+str(e)+' <<<<<<<<<<<<<<<<<')
    return response
