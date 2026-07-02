import pandas as pd


#Aggregate function

def aggregate(input_df: pd.DataFrame, group_by:str, metric:str,agg_fn:str)-> dict : 
    
    try:
    
        if agg_fn == 'sum':
            result = input_df.groupby(group_by)[metric].sum()   

        elif agg_fn == 'mean':
            result = input_df.groupby(group_by)[metric].mean()   

        elif agg_fn == 'count':
            result = input_df.groupby(group_by)[metric].count()   

        elif agg_fn == 'min':
            result = input_df.groupby(group_by)[metric].min()   

        elif agg_fn == 'max':
            result = input_df.groupby(group_by)[metric].max()   

        else :
            return {"error": "unsupported agg_fn; use sum, mean, count, min, or max"}
    
    except Exception as e:
        return {"error": f"could not aggregate: {e}"}

    
    return result.to_dict()




def filter_rows(input_df: pd.DataFrame, column: str , operator:str ,value: str | int | float) -> dict :
    try:
        if operator == '==':
            result = input_df[input_df[column] == value]
        elif operator == "!=":
            result = input_df[input_df[column] != value]
        elif operator == ">":
            result = input_df[input_df[column] > value]
        elif operator == "<":
            result = input_df[input_df[column] < value]
        elif operator == ">=":
            result = input_df[input_df[column] >= value]
        elif operator == "<=":
            result = input_df[input_df[column] <= value]
        else:
             return {'error':'Unsupported operator'}
    except Exception as e:
        return {'error': f'could not filter: {e}'}

    return {
            "row_count": len(result),
            "rows": result.to_dict(orient="records"),
            }
