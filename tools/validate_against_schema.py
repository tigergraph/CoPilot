class MapQuestionToSchemaException(Exception):
    pass

def validate_schema(conn, v_types, e_types, v_attrs, e_attrs):
    vertices = conn.getVertexTypes()
    edges = conn.getEdgeTypes()
    for v in v_types:
        if v in vertices:
            attrs = [x["AttributeName"] for x in conn.getVertexType(v)["Attributes"]]
            for attr in v_attrs.get(v, []):
                if attr not in attrs:
                    raise MapQuestionToSchemaException(attr + " is not found for " + v + " in the data schema. Run MapQuestionToSchema to validate schema." )
        else:
            raise MapQuestionToSchemaException(v + " is not found in the data schema. Run MapQuestionToSchema to validate schema.")

    for e in e_types:
        if e in edges:
            attrs = [x["AttributeName"] for x in conn.getEdgeType(e)["Attributes"]]
            for attr in e_attrs.get(e, []):
                if attr not in attrs:
                    raise MapQuestionToSchemaException(attr + " is not found for " + e + " in the data schema. Run MapQuestionToSchema to validate schema.")
        else:
            raise MapQuestionToSchemaException(e + " is not found in the data schema. Run MapQuestionToSchema to validate schema.")