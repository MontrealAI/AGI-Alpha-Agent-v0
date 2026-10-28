# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2013, Jeffrey W. Miller. See MILLER_HARRISON_LICENSE.txt.
# Python 3 compatibility only: dict membership and mutable range list.
# Python implementation

import random

def conjugate(q,L):
    '''Compute the conjugate vector of q (with a dummy 0 for the 0s).'''
    # count vector of q (including 0s)
    q_count = [0]*L
    for i in q: q_count[i] += 1
    # conjugate of q
    return [0]+[sum(q_count[i:]) for i in range(1,L)]

    
# Binomial coefficients
binomial = {}
binomial[0,0] = 1
def precompute_binomial(max_n):
    '''Precompute the binomial coefficients with values up to max_n.'''
    for k in range(1,max_n+1):
        binomial[0,k] = 0
    for n in range(1,max_n+1):
        binomial[n,0] = 1
        for k in range(1,max_n+1):
            binomial[n,k] = binomial[n-1,k] + binomial[n-1,k-1]

            
def count(p,q):
    '''Count the number of binary matrices with row sums p and column sums q.
    This function returns the number, and a lookup table that can be used for sampling.'''
    
    m,n = len(p),len(q)
    L = max(q)+2

    # Compute the conjugate of q
    c = conjugate(q,L)

    # Initialize p
    p = p[:] # make a copy, so we don't modify the input argument
    permutation = sort(p)
    
    # Pad p with zeros (including a 0 in front to make it like Matlab indexing)
    p = [0] + p + [0]*L
    
    # Precompute all the binomial coefficients that we might need
    precompute_binomial(n)

    # Initialize a new hash table
    table = {}
    root = (0,)*L
    table[root] = 1
    
    # count the number of matrices
    number = count_recursion_binary(p,c,1,1,0,p[2],c[1],table,L)
    table[tuple(c)] = number
    
    return number,table
    

# Recursion used for counting
def count_recursion_binary(p,c,j,k,s_sum,p_sum,c_sum,table,L):
    
    if s_sum==p[j]:
        # lookup the value or compute it if unknown
        c_s = tuple(c)
        if c_s in table:
            result = table[c_s]
        else:
            result = count_recursion_binary(p,c,j+1,1,0,p[j+2],c_s[1],table,L)
            if c[1] != p[j+1]: table[c_s] = result   
    else:
        r_k = c[k]-c[k+1]
        
        # Upper bound on s_k according to Gale-Ryser
        GR_condition = c_sum - s_sum - p_sum

        # range of values to sum over for s_k
        smallest = max(0, p[j]-s_sum-c[k+1])
        largest = min(min(r_k, p[j]-s_sum), GR_condition)

        result = 0
        for s_k in range(smallest,largest+1):
            c[k] -= s_k
            value = count_recursion_binary(p,c,j,k+1, s_sum+s_k, p_sum+p[j+k+1], c_sum+c[k+1],table,L)
            c[k] += s_k
            result += binomial[r_k,s_k]*value
        
    return result
    
    
def sample(p,q,number_of_samples,table):
    '''Draw number_of_samples from the uniform distribution on binary matrices with margins (p,q).
    The argument 'table' is the lookup table returned by count(p,q).'''
    
    m,n = len(p),len(q)
    L = max(q)+2

    # Compute the conjugate of q
    c = conjugate(q,L)

    # Initialize p
    p = p[:] # make a copy, so we don't modify the input argument
    permutation = sort(p)
    
    # Pad p with zeros (including a 0 in front to make it like Matlab indexing)
    p = [0] + p + [0]*L
    
    # Precompute all the binomial coefficients that we might need
    precompute_binomial(n)

    # get the total number of matrices
    number = table[tuple(c)]
    
    samples = []
    for k in range(number_of_samples):
        # Initialize S with all zeros
        S = []
        for i in range(m+1): S.append([0]*L)
        
        sample_recursion_binary(number,p,c,S,1,1,0,p[2],c[1],table,m,L)
        matrix = sample_matrix_entries(S,m,q,c,permutation)
        samples.append(matrix)
    return samples
    
    
# Recursion used for sampling
def sample_recursion_binary(number,p,c,S,j,k,s_sum,p_sum,c_sum,table,m,L):
    
    if (s_sum==p[j]):  # proceed to the next row
    
        if (j == m+1): return  # if we are done, return
        
        else: sample_recursion_binary(number,p,c,S,j+1,1,0,p[j+2],c[1],table,m,L)  # otherwise, recurse
        
    else:
        r_k = c[k]-c[k+1]
        
        # Upper bound on s_k according to Gale-Ryser
        GR_condition = c_sum - s_sum - p_sum

        # range of values to sum over for s_k
        smallest = max(0, p[j]-s_sum-c[k+1])
        largest = min(min(r_k, p[j]-s_sum), GR_condition)

        # Sample uniformly from {0,1,...,number-1}
        uniform_number = random.randint(0,number-1)
        
        # Find the value of s_k to use
        result = 0
        for s_k in range(smallest,largest+1):
            c[k] -= s_k
            value = count_recursion_binary(p,c,j,k+1, s_sum+s_k, p_sum+p[j+k+1], c_sum+c[k+1],table,L)
            result += binomial[r_k,s_k]*value
            
            if result>uniform_number:
                S[j][k] = s_k
                sample_recursion_binary(value,p,c,S,j,k+1,s_sum+s_k,p_sum+p[j+k+1],c_sum+c[k+1],table,m,L)
                c[k] += s_k
                return
            
            c[k] += s_k
        
        raise Exception("Internal error: This should be unreachable!")
    
    return


def sort(x):
    '''Sort x in descending order, and return the permutation used. '''
    m = len(x)
    y = list(range(m))
    for i in range(m):
        for j in range(m-1):
            if (x[j] < x[j+1]):
                x[j],x[j+1] = x[j+1],x[j]
                y[j],y[j+1] = y[j+1],y[j]
    return y
    

def sample_subset(x,n,k):
    ''' Uniformly sample a subset of size k from n elements. '''
    # initialize x to all zeros
    for i in range(n): x[i] = 0
    
    # sample without replacement
    for i in range(k):
        v = random.randint(0,n-i-1)
        j = 0
        while (v>=0):
            if (x[j]==0): v -= 1
            j += 1
        x[j-1] = 1


def sample_matrix_entries(S,m,q,c,permutation):
    ''' Sample a matrix corresponding to S. '''
    
    n = len(q)
    L = max(q)+2
    
    # make copies of q and c
    u = q[:]
    d = c[:]
    # allocate subset indicator vector
    x = [0]*n
    # allocate matrix
    matrix = []
    for i in range(m): matrix.append([0]*n)
    
    for j in range(1,m+1):
        for k in range(1,L-1):
            r_k = d[k]-d[k+1]
            sample_subset(x, r_k, S[j][k])
            i = 0
            s = 0
            while (s < r_k):
                if (u[i]==k):
                    matrix[permutation[j-1]][i] = x[s]
                    u[i] -= x[s]
                    s += 1
                i += 1
            d[k] -= S[j][k]

    return matrix







