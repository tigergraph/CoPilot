class MapQuestionToSchemaException(Exception):
    pass

class InvalidFunctionCallException(Exception):
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


def validate_function_call(conn, generated_call: str, retrieved_docs: list) -> str:
    # handle installed queries
    valid_headers = [doc.metadata.get("function_header") for doc in retrieved_docs]
    if "runInstalledQuery(" == generated_call[:18]:
        query_name = generated_call.split(",")[0].split("runInstalledQuery(")[1]
        if query_name in valid_headers:
            return generated_call
        else:
            raise InvalidFunctionCallException(generated_call + " is not an acceptable function. Please select from the retrieved functions.")
    elif "conn." == generated_call[:5]:
        return validate_function_call(conn, generated_call.strip("conn."), retrieved_docs)
    else: # handle pyTG functions
        if generated_call.split("(")[0] in valid_headers: # could do more type parsing for args and things here, but will let it be for now.
            return generated_call
        else:
            raise InvalidFunctionCallException(generated_call + " is not an acceptable function. Please select from the retrieved functions.")