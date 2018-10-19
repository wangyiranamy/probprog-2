import tensorflow as tf
import edward as ed
import pickle
from edward.models import Dirichlet, ParamMixture, Categorical, Empirical


class LDACavi(object):
    def __init__(self, K, V, D, N):
        self.K = K
        self.V = V
        self.D = D
        self.N = N
        alpha = tf.ones([K])/K
        yita = tf.ones([V])/V
        self.theta = [None] * D
        self.beta = Dirichlet(yita, sample_shape=K)
        self.z = [None] * D
        self.w = [None] * D
        for d in range(D):
            self.theta[d] = Dirichlet(alpha)
            self.w[d] = ParamMixture(mixing_weights=self.theta[d],
                                     component_params={'probs': self.beta},
                                     component_dist=Categorical,
                                     sample_shape=N[d],
                                     validate_args=True)
            self.z[d] = self.w[d].cat

    def __run_inference__(self, T):
        self.inference.initialize(n_iter=T, n_print=10, logdir='log')
        tf.global_variables_initializer().run()
        for _ in range(self.inference.n_iter):
            info_dict = self.inference.update()
            self.inference.print_progress(info_dict)
        self.inference.finalize()

    def gibbs(self, wordIds, S, T):
        K = self.K
        V = self.V
        D = self.D
        N = self.N
        latent_vars = {}
        training_data = {}
        qbeta = Empirical(tf.Variable(tf.zeros([S, K, V])))
        latent_vars[self.beta] = qbeta
        qtheta = [None] * D
        qz = [None] * D
        for d in range(D):
            qtheta[d] = Empirical(tf.Variable(tf.ones([S, K]) / K))
            latent_vars[self.theta[d]] = qtheta[d]
            qz[d] = Empirical(tf.Variable(tf.zeros([S, N[d]], dtype=tf.int32)))
            latent_vars[self.z[d]] = qz[d]
            training_data[self.w[d]] = wordIds[d]
        self.latent_vars = latent_vars
        self.inference = ed.Gibbs(latent_vars, data=training_data)
        print("gibbs setup finished")
        self.__run_inference__(T)

    def criticize(self, tokens):
        K = self.K
        qbeta_sample = self.latent_vars[self.beta].params[-1].eval()
        pickle.dump(qbeta_sample, open("train2.p", "wb"))
        prob = [None] * K
        for k in range(K):
            prob[k] = qbeta_sample[k, :]
            print(len(prob[k]))
        tokens_probs = [None] * K
        for k in range(K):
            tokens_probs[k] = dict((t, p) for t, p in zip(tokens, prob[k]))
            newdict = sorted(tokens_probs[k],
                             key=tokens_probs[k].get,
                             reverse=True)[:15]
            print('topic %d' % k)
            for word in newdict:
                print(word, tokens_probs[k][word])
