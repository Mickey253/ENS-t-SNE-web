import numpy as np 
import pylab as plt 
import scipy
import pylab as plt
from tqdm import tqdm
# from numba import njit

import matplotlib

MACHINE_EPSILON = 1e-15

tab10 = {0: "red", 
        1: "blue",
        2: "orange",
        3: "tab:red",
        4: "tab:purple",}

colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple", "black", "lightblue", "pink", "yellow", "brown"]
markers = ["o", "s", "v", "p", "*", "^" ]
fillstyles = ["full", "none", "top", "bottom", "left", "right"]

markerstyles = [
    colors,
    markers,
    fillstyles
]

cmap = plt.get_cmap("cool")

def vis_2d(data,labels,title=None):
    fig, axes = plt.subplots(1,len(data))

    pair_labels = np.zeros((data[0].shape[0], 3),dtype=np.int32)
    for i in range(data[0].shape[0]):
        for j in range(len(labels)): pair_labels[i,j] = labels[j][i]

    num_clusts = np.max(pair_labels,axis=0)
    print(labels[0])

    color = dict(zip(range(10), [i/10 for i in range(10)]))
    l = 0
    for ax, X in zip(axes,data):
        plt.clf()
        fig, ax = plt.subplots()
        for i in range(num_clusts[0] + 1):
            for j in range(num_clusts[1] + 1):
                for k in range(num_clusts[2] + 1):
                    emb = X[ (pair_labels[:,0] == i) & (pair_labels[:,1] == j) & (pair_labels[:,2] == k) ]
                    x,y = emb[:,0], emb[:,1]
                    style = matplotlib.markers.MarkerStyle(markers[j],fillstyle=fillstyles[k])
                    print(color[i])
                    ax.scatter(x,y,c=cmap(color[i]),marker=style,alpha=1,linewidths=1)
                    plt.xticks(color="w")
                    plt.yticks(color="w")
        if title: plt.savefig(f"{title}_{l}.png")
        l += 1

    if title: plt.savefig(title)
    else: plt.show()

def vis_3d(X, labels, title=None):

    fig = plt.figure()
    ax = fig.add_subplot(1,1,1,projection='3d')

    pair_labels = np.zeros((X.shape[0], 3),dtype=np.int32)
    for i in range(X.shape[0]):
        for j in range(len(labels)): pair_labels[i,j] = labels[j][i]

    num_clusts = np.max(pair_labels,axis=0)

    for i in range(num_clusts[0] + 1):
        for j in range(num_clusts[1] + 1):
            for k in range(num_clusts[2] + 1):
                emb = X[(pair_labels[:,0] == i) & (pair_labels[:,1] == j) & (pair_labels[:,2] == k)]
                x,y,z = emb[:,0], emb[:,1], emb[:,2]
                style = matplotlib.markers.MarkerStyle(markers[j],fillstyle=fillstyles[k])
                ax.scatter(x,y,z,c=colors[i], marker=style, alpha=0.9)
    plt.xticks(color="w")
    plt.yticks(color="w")
    ax.set_zticks(ax.get_zticks(), [" " for _ in ax.get_zticks()])

    if title: plt.savefig(f"{title}.png")
    else: plt.show()    



def get_clusters(n_points, n_clusters=[2], n_dimensions=[2], noise=0.1, random_state=None):

    from sklearn.datasets import make_blobs
    data = np.zeros((n_points, sum(n_dimensions)))
    labels = list()
    subspaces = list()
    cur_dim = 0
    for n_clust, n_dim in zip(n_clusters,n_dimensions):
        tmp,lab = make_blobs(n_points,n_features=n_dim,centers=n_clust, random_state=random_state)
        labels.append(lab)
        data[:,cur_dim:n_dim+cur_dim] = tmp 
        subspaces.append(tmp)
        cur_dim += n_dim
    
    return data, labels, subspaces

# @njit
def inv_sq(embedding):
    """
    Computes the pairwise inverse square law distances for the given embedding. 
    These are given by q_ij = 1/(1+|y_i-y_j|^2) for a given pair (i,j). The set 
    of probabilities used in the low dimensional map of tSNE can then be computed
    by dividing by the sum.

    Parameters
    ----------

    embedding : array, shape (n_samples,dim)
    Embedding (coordinates in low-dimensional map).

    Returns
    dist: pairwise inverse square law distances, as a condensed 1D array.
    """
    dist = scipy.spatial.distance.pdist(embedding,metric='sqeuclidean')
    dist += 1.0
    dist **= -1.0
    return dist    

# @njit
def joint_probabilities(distances, perplexity):
    """\
    Computes the joint probabilities p_ij from given distances (see tsne paper).

    Parameters
    ----------

    distances : array, shape (n_samples*(n_samples-1)/2,)
    Pairwise distances, given as a condensed 1D array.

    perpelxity : float, >0
    Desired perplexity of the joint probability distribution.
    
    Returns
    -------

    P : array, shape (n_samples*(n_samples-1)/2),)
    Joint probability matrix, given as a condensed 1D array.
    """
    #change condensed distance array to square form
    # print(distances.shape)
    # distances = scipy.spatial.distance.squareform(distances)
    n_samples = len(distances)
    
    #find optimal neighborhood parameters to achieve desired perplexity
    lower_bound=1e-1; upper_bound=1e1; iters=10 #parameters for binary search
    sigma = np.empty(n_samples) #bandwith array
    for i in range(n_samples):
        D_i = np.delete(distances[i],i) #distances to ith sample
        estimate = np.sum(D_i)/(n_samples-1)/5
        lower_bound_i=lower_bound*estimate; upper_bound_i=upper_bound*estimate;
        for iter in range(iters):
            #initialize bandwith parameter for sample i:
            sigma_i = (lower_bound_i*upper_bound_i)**(1/2)
            #compute array with conditional probabilities w.r.t. sample i:
            P_i = np.exp(-D_i**2/(2*sigma_i**2))
            if np.isfinite(P_i).all() is False:
                print('infinite value')
            if np.nan in P_i:
                print('nan found')
            if np.sum(P_i) == 0:
                print('adds to 0')
            P_i /= np.maximum(np.sum(P_i),1e-15)
            #compute perplexity w.r.t sample i:
            HP_i = -np.dot(P_i,np.log2(P_i+1e-15))
            PerpP_i = 2**(HP_i)
            #update bandwith parameter for sample i:
            if PerpP_i > perplexity:
                upper_bound_i = sigma_i
            else:
                lower_bound_i = sigma_i
        #final bandwith parameter for sample i:
        sigma[i] = (lower_bound_i*upper_bound_i)**(1/2)

    #compute conditional joint probabilities (note: these are transposed)
    conditional_P = np.exp(-distances**2/(2*sigma**2))
    np.fill_diagonal(conditional_P,0)
    conditional_P /= np.sum(conditional_P,axis=0)

    #compute (symmetric) joint probabilities
    P = (conditional_P + conditional_P.T) #/ (2*n_samples)
    P = scipy.spatial.distance.squareform(P, checks=False)
    sum_P = np.maximum(np.sum(P), 1e-15)
    P = np.maximum(P/sum_P, 1e-15)
    
    return P

def KL(X, P):
    """
    X: realized embedding 
    P: joint probabilites 
    """
    dist = inv_sq(X)
    Q = np.maximum(dist/(np.sum(dist)), 1e-15)

    kl_divergence = 2.0 * np.dot(
        P, np.log(np.maximum(P/Q, 1e-15)))
    return kl_divergence

def enstsne_cost(P: list[np.ndarray], joints: list[np.ndarray], X: np.ndarray):
    """
    P: a list of 2x3 projection matrices of X 
    joints: list of nxn joint probabilities for projection of X
    X: a nx3 dimensional embedding of the data
    """
    return sum(KL(X @ p.T, j) for p,j in zip(P,joints))

def KL_grad(embedding,P):
    dist = inv_sq(embedding)
    Q = np.maximum(dist/(np.sum(dist)), MACHINE_EPSILON)
    
    # kl_divergence = 2.0 * np.dot(
    #     P, np.log(np.maximum(P/Q, MACHINE_EPSILON)))

    grad = np.ndarray(embedding.shape)
    PQd = scipy.spatial.distance.squareform((P-Q)*dist)
    for i in range(len(embedding)):
        grad[i] = np.dot(np.ravel(PQd[i],order='K'),embedding[i]-embedding)
    grad *= 4

    return grad

def x_grad(P: list[np.ndarray], joints: list[np.ndarray], X: np.ndarray):
    grads = [KL_grad(X @ p.T, j) for p,j in zip(P,joints)]
    return sum(g @ p for g,p in zip(grads,P)), grads

def pi_grad(P:list[np.ndarray], joints: list[np.ndarray], X: np.ndarray):
    return [KL_grad(X @ p.T, j).T @ X  for p,j in zip(P,joints)] 

def grad(P: list[np.ndarray], joints: list[np.ndarray], X: np.ndarray):
    grads = [KL_grad(X @ p.T, j) for p,j in zip(P,joints)]
    dx = sum(g @ p for g,p in zip(grads, P)) / len(joints)
    dp = [g.T @ X for g in grads]
    return dx, dp

matrices = [np.array([[1,0,0],
                      [0,1,0]]),
            np.array([[0,1,0],
                      [0,0,1]]),
            np.array([[0,0,1],
                     [1,0,0]])
]

class ENSTSNE():
    def __init__(self, data, perplexity,labels=None,early_exaggeration=12.0,fixed=False):
        self.perplexity = perplexity
        self.data = data
        # self.projections = [np.random.uniform(-1,1,(2,3)) for _ in range(len(data))]
        self.projections = [matrices[i] for i in range(len(self.data))]
        self.joints = [joint_probabilities(d,perplexity) for d in data]

        self.n_proj = len(self.projections)
        self.labels = labels

        self.ee = early_exaggeration
        self.fixed = fixed

        # self.X = np.random.uniform(-1,1,(data[0].shape[0], 3))

        from sklearn.decomposition import PCA
        self.X = PCA(3).fit_transform(sum(data) / len(data))

    def gd(self,maxiter,momentum=0.9,lr=100,tol=1e-5,folder=None):
        X = self.X 
        P = self.projections
        joints = [j * self.ee for j in self.joints]
        # joints = self.joints

        lr = X.shape[0] / self.ee / 4 
        lr = np.maximum(lr, 50)
        
        lrp = lr / (50/0.01)
        print(lrp)

        change = 0. 
        hist = [enstsne_cost(P,joints,X)]

        self.X = X.copy() 
        self.P = P   
        fixed = True

        momentum = 0.5
        for i in tqdm(range(maxiter)):

            dx, dp = grad(P, joints, X)
            X -= lr * dx + momentum * change
            if not fixed: 
                P = [p - ( lrp * newc) for p,newc in zip(P,dp)]

            change = dx
            if i == 250: 
                momentum = 0.8 
                joints = self.joints
                fixed = self.fixed

            if i % 200 == 0 and i > 0:
                lr /= 2


            hist.append(enstsne_cost(P,self.joints,X))


        self.X = X 
        self.P = P 
        self.hist = hist

        return hist

    def vis_2d(self,title=None):
        colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple"]
        markers = ["o", "^", "x"]        
        fig, axes = plt.subplots(1,self.n_proj)
        for i,(ax, p) in enumerate(zip(axes,self.P)):
            print(self.X.shape, p.shape)
            x = self.X @ p.T
            if self.labels: 
                l1max, l2max = np.max(self.labels[0]), np.max(self.labels[1])

                for i in range(l1max+1):
                    for j in range(l2max+1):
                        print(i, j)
                        emb = x[(self.labels[0] == i) & (self.labels[1] == j)]
                        ax.scatter(emb[:,0],emb[:,1], c=colors[i], marker=markers[j])
            else: ax.scatter(x[:,0], x[:,1])
        if title: 
            plt.savefig(title)
        # else: plt.show()
        # plt.clf()
        # plt.close(fig)
    
    def vis_3d(self,title=None):
        colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple"]
        markers = ["o", "^", "x"]

        fig = plt.figure(figsize=(10,10))
        ax = fig.add_subplot(1,1,1,projection='3d')

        l1max, l2max = np.max(self.labels[0]), np.max(self.labels[1])

        for i in range(l1max+1):
            for j in range(l2max+1):
                emb = self.X[(self.labels[0] == i) & (self.labels[1] == j)]
                x,y,z = emb[:,0], emb[:,1], emb[:,2]
                ax.scatter(x,y,z,c=colors[i], marker=markers[j],alpha=0.9)

        # x,y,z = self.X[:,0], self.X[:,1], self.X[:,2]
        # ax.scatter(x,y,z,alpha=0.9)

        Q = self.P[0]
        print(np.cross(Q[0],Q[1]))

        for k in range(len(self.labels)):
            Q = self.P[k]
            q = np.cross(Q[0],Q[1])       
            ind = np.argmax(np.sum(q[k]*self.X,axis=1))
            m = np.linalg.norm(self.X[ind])/np.linalg.norm(q)
            print(np.linalg.norm(q[k]), q)
            ax.plot([0,m*q[0]],[0,m*q[1]],[0,m*q[2]],'--',
                    linewidth=4.5,
                    color='gray')        

        plt.savefig(title)

        plt.clf()
        plt.close(fig)

    def get_images(self):
        return [self.X @ p.T for p in self.P]
    def get_embedding(self):
        return self.X
    

def map_to_int(data: list[any]):
    unq = np.unique(data)
    int_map = {u: i for i,u in enumerate(unq)}
    return np.array([int_map[u] for u in data])
    
from sklearn.metrics import pairwise_distances
def load_clusters(n=100, dims= [5,6], n_clusters = [2,3]):

    X, labels,subspaces = get_clusters(n,n_clusters,dims)
    
    dists = [pairwise_distances(x) for x in subspaces]

    return dists, labels, X

def load_penguins():
    import pandas as pd 
    data = pd.read_csv("application/static/data/input/palmerpenguins.csv")
    x1 = data[["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]].to_numpy()
    x1 /= np.max(x1,axis=0)
    x2 = map_to_int(data[["sex"]].to_numpy().reshape((-1)))

    l1 = map_to_int(data[["species"]].to_numpy().reshape((-1)))

    return [pairwise_distances(x1), pairwise_distances(x2.reshape(-1,1))], [l1, x2], np.concatenate([x1,x2.reshape(-1,1)],axis=1)

def load_fashion(ssize=300):
    data = np.load("datasets/fashion_mnist/X.npy")
    y = np.load("datasets/fashion_mnist/y.npy")

    data /= np.max(data,axis=0)

    data = data[(y == 0) | (y == 3) | (y == 8)]
    y = y[(y == 0) | (y == 3) | (y == 8)]

    print(data.shape)

    ind = np.random.choice(data.shape[0],ssize)

    x1 = data[:,:784//2]
    x2 = data[:,784//2:]

    x1,x2 = x1[ind], x2[ind]
    y = y[ind]

    y = map_to_int(y)
    return [pairwise_distances(x1), pairwise_distances(x2)], [y,y], np.concatenate([x1,x2], axis=1)

def load_mnist(ssize=300):
    data = np.loadtxt("datasets/mnist_test.csv",dtype=np.float64, delimiter=",", skiprows=1)
    data, y = data[:,1:], data[:,0]

    data /= np.maximum(np.max(data,axis=0),1e-15)

    a,b,c = 1,7,2
    data = data[(y == a) | (y == b) | (y == c)]
    y = y[(y == a) | (y == b) | (y == c)]

    print(data.shape)

    ind = np.random.choice(data.shape[0],ssize)

    x1 = data[:,:784//2]
    x2 = data[:,784//2:]

    x1,x2 = x1[ind], x2[ind]
    y = y[ind]

    y = map_to_int(y)
    return [pairwise_distances(x1), pairwise_distances(x2)], [y,y], np.concatenate([x1,x2], axis=1)

def load_cc():
    import pandas as pd 
    data = pd.read_csv("datasets/cc_data.csv")
    data["income"] /= np.max(data["income"])

    data["gender"][data["gender"] == "'M'"] = 1.0
    data["gender"][data["gender"] == "'F'"] = 0.0

    data["education"][data["education"] == "'Lower secondary'"] = 0.0
    data["education"][data["education"] == "'Secondary / secondary special'"] = 1.0
    data["education"][data["education"] == "'Incomplete higher'"] = 2.0 
    data["education"][data["education"] == "'Higher education'"] = 3.0           

    data["education"] /= np.max(data["education"])

    x = data.to_numpy()

    return [pairwise_distances(x[:,0].reshape(-1,1)), pairwise_distances(x[:,1].reshape(-1,1)), pairwise_distances(x[:,2].reshape(-1,1))], [np.zeros_like(x[:,0]), x[:,1], (3.0 * x[:,2]).astype(int)], x

def load_auto():
    import pandas as pd 
    data = pd.read_csv("mview/samples/car_mpg/auto-mpg_mod.csv")

    x1 = data[["mpg", "cylinders", "displacement"]].to_numpy()
    x2 = data[["horsepower", "weight", "acceleration"]].to_numpy()
    x2 /= np.max(x2,axis=0)

    y1 = np.array([0 if x1[i,1] <=4 else 1 if x1[i,1] <= 6 else 2 for i in range(x1.shape[0])])
    x1 /= np.max(x1,axis=0)

    quants = np.quantile(x2[:,1], [0.25, 0.5, 0.75])
    y2 = np.array( [0 if x2[i,1] < quants[0] else 1 if x2[i,1] < quants[1] else 2 if x2[i,1] < quants[2] else 3 for i in range(x2.shape[0])] )

    return [pairwise_distances(x1), pairwise_distances(x2)], [y1,y2], np.concatenate([x1,x2], axis=1)

def load_food():
    import pandas as pd 
    data = pd.read_csv("datasets/food_comp/food_comp_processed.csv")

    x1 = data[['Water_(g)','Vit_E_(mg)','Sodium_(mg)','Lipid_Tot_(g)','Energ_Kcal']].to_numpy()
    x2 = data[['Protein_(g)', 'Vit_B6_(mg)', 'Vit_B12_(µg)', 'Vit_D_µg']].to_numpy()    
    x1 /= np.max(x1, axis=0)
    x2 /= np.max(x2, axis=0)

    y = np.loadtxt("datasets/food_comp/food_comp_clusterids.csv")

    return [pairwise_distances(x1), pairwise_distances(x2)], [y,y], np.concatenate([x1,x2], axis=1)

def load_wine(a=[0,1,2],b=[3,4,5]):
    import pandas as pd 
    data = pd.read_csv("datasets/wine/winequality.csv")

    x = data.to_numpy()

    ind = np.random.choice(data.shape[0],3000)    
    x = x[ind, :]

    y1 = x[:, 11].copy()

    x /= np.max(x,axis=0)
    x1 = x[:,a]
    x2 = x[:,b]

    # _,y1 = np.unique(y1,return_inverse=True)
    # y1 /= np.max(y1)
    y2 = x[:, 12]

    return [pairwise_distances(x1), pairwise_distances(x2)], [y1,y2], x




if __name__ == "__main__":
    # dists, labels = load_fashion()

    # dists, labels = load_clusters(n=300, dims=[10,10], n_clusters=[4,3])
    # dists, labels, X = load_wine()
    
    # enstsne = ENSTSNE(dists,30,labels=labels)
    # enstsne.gd(1000)
    # vis_2d(enstsne.get_images(),labels,"test")

    m = 10
    count = 0
    dims = list()
    for num in range(2 ** (2*m)):
        res = [int(i) for i in list('{0:0b}'.format(num))]
        res = [0] * (2*m-len(res)) + res
        a,b = res[:m], res[m:]
        if sum(a) <= 3 or sum(b) <= 3 or a == b:
            count += 1
            continue 
        c = [[i for i,c in enumerate(a) if c == 1], [i for i,c in enumerate(b) if c == 1]]
        
        a = set(c[0])
        b = set(c[1])
        if len(a.intersection(b)) > 1 or a.intersection(b) == a or a.intersection(b) == b:
            count += 1
            continue

        dims.append(c)

    import random 
    random.shuffle(dims)
    for i,(dim1, dim2) in enumerate(dims):
        print(i)
        print()
        dists,labels, _ = load_wine(dim1,dim2)
        enstsne = ENSTSNE(dists,30,labels=labels)
        enstsne.gd(2000)
        vis_2d(enstsne.get_images(),labels,f"figs/wines/2d_{dim1}_{dim2}")
        vis_3d(enstsne.get_embedding(),labels,f"figs/wines/3d_{dim1}_{dim2}")