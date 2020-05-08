
{
    'name': 'Physical Stock Correction',
    'version': '12.0.0.0',
    'category': 'General',
	'summary': 'Physical Stock Correction',
	'author': 'Maneesha Suveesh',
    'website': '',
    'description': """""",
    'depends': [
        'base',
        'stock',
        'product_expiry'

    ],
    'data': [
     'security/security_group.xml',
     'security/ir.model.access.csv',
     'views/stock_correction_view.xml',
     'data/ir_sequence_data.xml'
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
