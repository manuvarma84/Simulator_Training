import ast
import operator as op

# Safe evaluation parameters
allowed_operators = {
    ast.Add: op.add, ast.Sub: op.sub, 
    ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Pow: op.pow, ast.BinOp: ast.BinOp,
    ast.USub: op.neg
}

def safe_eval(expr, variables):
    return eval_(ast.parse(expr, mode='eval').body, variables)

def eval_(node, variables):
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.Name):
        return variables.get(node.id, 0)
    elif isinstance(node, ast.BinOp):
        return allowed_operators[type(node.op)](
            eval_(node.left, variables),
            eval_(node.right, variables)
        )
    elif isinstance(node, ast.UnaryOp):
        return allowed_operators[type(node.op)](eval_(node.operand, variables))
    else:
        raise TypeError(f"Unsupported operation: {node}")

def calculate_analytics(analytics_config, inputs):
    results = {}
    variables = {k: float(v) if '.' in v else int(v) for k, v in inputs.items()}
    
    for analysis in analytics_config:
        output_key = analysis.get('output')
        formula = analysis.get('formula')
        if output_key and formula:
            try:
                results[output_key] = safe_eval(formula, variables)
            except Exception as e:
                results[output_key] = None
        else:
            print(f"Skipping invalid analysis config: {analysis}")
    return results