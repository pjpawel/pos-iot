import itertools

markers = ["1","2","3","4","8","s","p","P","*","h","H","+","x","X","D","d","|","_",]
line_styles = ["-", "--", ":", "-."]
styles = itertools.cycle([marker + line for marker in markers for line in line_styles])