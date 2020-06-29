import math
import sys
from collections import defaultdict
import itertools
from grammar import Pcfg


def check_table_format(table):
    """
    Return true if the backpointer table object is formatted correctly.
    Otherwise return False and print an error.  
    """
    if not isinstance(table, dict): 
        sys.stderr.write("Backpointer table is not a dict.\n")
        return False
    for split in table: 
        if not isinstance(split, tuple) and len(split) ==2 and \
          isinstance(split[0], int)  and isinstance(split[1], int):
            sys.stderr.write("Keys of the backpointer table must be tuples (i,j) representing spans.\n")
            return False
        if not isinstance(table[split], dict):
            sys.stderr.write("Value of backpointer table (for each span) is not a dict.\n")
            return False
        for nt in table[split]:
            if not isinstance(nt, str): 
                sys.stderr.write("Keys of the inner dictionary (for each span) must be strings representing nonterminals.\n")
                return False
            bps = table[split][nt]
            if isinstance(bps, str): # Leaf nodes may be strings
                continue 
            if not isinstance(bps, tuple):
                sys.stderr.write("Values of the inner dictionary (for each span and nonterminal) must be a pair ((i,k,A),(k,j,B)) of backpointers. Incorrect type: {}\n".format(bps))
                return False
            if len(bps) != 2:
                sys.stderr.write("Values of the inner dictionary (for each span and nonterminal) must be a pair ((i,k,A),(k,j,B)) of backpointers. Found more than two backpointers: {}\n".format(bps))
                return False
            for bp in bps: 
                if not isinstance(bp, tuple) or len(bp)!=3:
                    sys.stderr.write("Values of the inner dictionary (for each span and nonterminal) must be a pair ((i,k,A),(k,j,B)) of backpointers. Backpointer has length != 3.\n".format(bp))
                    return False
                if not (isinstance(bp[0], str) and isinstance(bp[1], int) and isinstance(bp[2], int)):
                    print(bp)
                    sys.stderr.write("Values of the inner dictionary (for each span and nonterminal) must be a pair ((i,k,A),(k,j,B)) of backpointers. Backpointer has incorrect type.\n".format(bp))
                    return False
    return True

def check_probs_format(table):
    """
    Return true if the probability table object is formatted correctly.
    Otherwise return False and print an error.  
    """
    if not isinstance(table, dict): 
        sys.stderr.write("Probability table is not a dict.\n")
        return False
    for split in table: 
        if not isinstance(split, tuple) and len(split) ==2 and isinstance(split[0], int) and isinstance(split[1], int):
            sys.stderr.write("Keys of the probability must be tuples (i,j) representing spans.\n")
            return False
        if not isinstance(table[split], dict):
            sys.stderr.write("Value of probability table (for each span) is not a dict.\n")
            return False
        for nt in table[split]:
            if not isinstance(nt, str): 
                sys.stderr.write("Keys of the inner dictionary (for each span) must be strings representing nonterminals.\n")
                return False
            prob = table[split][nt]
            if not isinstance(prob, float):
                sys.stderr.write("Values of the inner dictionary (for each span and nonterminal) must be a float.{}\n".format(prob))
                return False
            if prob > 0:
                sys.stderr.write("Log probability may not be > 0.  {}\n".format(prob))
                return False
    return True



class CkyParser(object):
    """
    A CKY parser.
    """

    def __init__(self, grammar): 
        """
        Initialize a new parser instance from a grammar. 
        """
        self.grammar = grammar

    def is_in_language(self,tokens):
        """
        Membership checking. Parse the input tokens and return True if 
        the sentence is in the language described by the grammar. Otherwise
        return False
        """
   
        n=len(tokens)
        init=[set([j for j,_,_ in self.grammar.rhs_to_rules[(i,)]]) for i in tokens]
        pi=[[set()]*(n+1) for i in range(n)]
        for i in range(n):
            pi[i][i+1]=init[i]
        for l in range(2,n+1):
            for i in range(n-l+1):
                j=i+l
                for k in range(i+1,j):
                    M=set([rule for b in pi[i][k] for c in pi[k][j] for rule,_,_ in self.grammar.rhs_to_rules[(b,c)]])
                    pi[i][j]=pi[i][j].union(M) 
        return self.grammar.startsymbol in pi[0][-1]
       
    def parse_with_backpointers(self, tokens):
        """
        Parse the input tokens and return a parse table and a probability table.
        """
   
        n=len(tokens)
        init=[set([(j,p) for j,_,p in self.grammar.rhs_to_rules[(i,)]]) for i in tokens]
        tb=defaultdict()
        pb=defaultdict()
        for i in range(n):
            tb[(i,i+1)]=defaultdict()
            pb[(i,i+1)]=defaultdict()
            for a,b in init[i]:
                tb[(i,i+1)][a]=tokens[i]
                pb[(i,i+1)][a]=math.log2(b)
        for length in range(2,n+1):
            for i in range(n-length+1):
                j=i+length
                pb[(i,j)]=defaultdict()
                tb[(i,j)]=defaultdict()
                L=[l for k in range(i+1,j) for x in pb[(i,k)] for y in pb[(k,j)] for l,_,_ in self.grammar.rhs_to_rules[(x,y)]]
                for l in L:
                    pb[(i,j)][l]=float("-Inf")
                    tb[(i,j)][l]=((0,0,0),(0,0,0))
                for k in range(i+1,j):
                    for x in pb[(i,k)]:
                        for y in pb[(k,j)]:
                            for l,_,p in self.grammar.rhs_to_rules[(x,y)]:
                                prob=math.log2(p)+pb[(i,k)][x]+pb[(k,j)][y]
                                if prob>pb[(i,j)][l]:
                                    #print((prob,pb[(i,j)][l],tb[(i,j)][l],((x,i,k),(y,k,j))))
                                    pb[(i,j)][l]=prob 
                                    tb[(i,j)][l]=((x,i,k),(y,k,j))

        return tb, pb 


def get_tree(chart, i,j,nt): 
    """
    Return the parse-tree rooted in non-terminal nt and covering span i,j.
    """
 
    x=chart[(i,j)][nt]
    if isinstance(x,tuple):
        return (nt,get_tree(chart,i,x[0][2],x[0][0]),get_tree(chart,x[0][2],j,x[1][0]))
    else:
        return (nt,x) 
 
       
if __name__ == "__main__":
    
    with open('./atis3.pcfg','r') as grammar_file: 
        grammar = Pcfg(grammar_file) 
        parser = CkyParser(grammar)
        toks =['flights', 'from','miami', 'to', 'cleveland','.'] 
        print(parser.is_in_language(toks))
        table,probs = parser.parse_with_backpointers(toks)
        assert check_table_format(table)
        assert check_probs_format(probs)
    print(check_table_format(table))
    print(check_probs_format(probs))
        
