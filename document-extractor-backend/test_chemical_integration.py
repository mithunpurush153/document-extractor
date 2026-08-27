from services.chemical_validator import ChemicalValidator


def make_tables(values, standard='ASTM A194/A194M', grade='8M'):
    chem = {
        'rows': 1, 'cols': 8,
        'columns': ['%C','%Mn','%P','%S','%Si','%Cr','Ni%','Mo'],
        'data': [{**values, 'row_label': 'OBSERVED COMPOSITIONS'}],
    }
    material = {
        'rows': 1, 'cols': 4,
        'columns': ['Material','Grade','Standard','Specification'],
        'data': [{'Material':'ROUND BAR','Grade':grade,'Standard':standard,'Specification':f'{standard} Grade {grade}'}],
    }
    return {'page_1': [chem, material]}


def run(name, values):
    result = ChemicalValidator().validate_supplier_document({'tables_by_page': make_tables(values)})
    summary = result['validation_result']['summary']
    print(name, result['identified_standard'], result['identified_grade'], summary)
    assert result['identified_standard'] == 'ASTM A194/A194M'
    assert result['identified_grade'] == '8M'
    assert summary['fail'] == 0
    assert summary['pass'] == 8
    assert summary['not_reported'] == 1


if __name__ == '__main__':
    run('M16', {'%C':'0.043','%Mn':'1.052','%P':'0.036','%S':'0.023','%Si':'0.250','%Cr':'16.108','Ni%':'10.457','Mo':'2.250'})
    run('M36', {'%C':'0.046','%Mn':'1.229','%P':'0.036','%S':'0.024','%Si':'0.100','%Cr':'16.052','Ni%':'10.625','Mo':'2.310'})
    print('CHEMICAL INTEGRATION TESTS PASSED')
