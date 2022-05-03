# It gives the (input,target) pairs from the dataset

def read_data(data_path):

    with open(data_path, "r", encoding="utf-8") as f:
        lines = [line.split("\t") for line in f.read().split("\n") if line != '']
    
    input, target = [val[1] for val in lines], [val[0] for val in lines]
   
    return input, target
