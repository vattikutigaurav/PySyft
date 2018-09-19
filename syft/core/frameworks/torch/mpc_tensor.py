from .tensor import _SyftTensor
from ....mpc import spdz
import syft as sy

class _MPCTensor(_SyftTensor):
    """
    Example of a custom overloaded _SyftTensor

    Role:
    Converts all add operations into sub/minus ones.
    """

    def __init__(self, shares, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fixme: remove the share on init, declaring a MPCTensor should autmatically create a _GeneralizedPointerTensor
        if isinstance(shares, sy._GeneralizedPointerTensor):
            raise TypeError('Should have a wrapper on the _GeneralizedPointerTensor')
        self.shares = shares  # shares is a _GeneralizedPointerTensor
        self.child = self.shares


    # The table of command you want to replace
    substitution_table = {
        'torch.add': 'torch.add',
        'torch.mul': 'torch.mul',
    }

    class overload_functions:
        """
        Put here the functions you want to overload
        Beware of recursion errors.
        """

        @staticmethod
        def get(attr):
            attr = attr.split('.')[-1]
            return getattr(sy._MPCTensor.overload_functions, attr)

    # Put here all the methods you want to overload

    def __add__(self, other):
        # gp_ stands for GeneralizedPointer
        gp_response = spdz.spdz_add(self.shares, other.shares)
        response = _MPCTensor(gp_response)
        # response.shares = shares
        return response

    def __mul__(self, other):
        workers = list(self.shares.child.pointer_tensor_dict.keys())
        gp_response = spdz.spdz_mul(self.shares, other.shares, workers)
        response = _MPCTensor(gp_response)
        return response

    def mm(self, other):
        workers = list(self.shares.child.pointer_tensor_dict.keys())
        gp_response = spdz.spdz_matmul(self.shares, other.shares, workers)
        response = _MPCTensor(gp_response)
        return response
       
    def send(self, workers):
        self.n_workers = len(workers)
        self.shares = self.share(self.var, self.n_workers)
        self.child = self.shares
        self.workers = workers
        for share, worker in zip(self.shares, self.workers):
            share.send(worker)

    def get(self):
        value = self.shares.child.sum_get() % spdz.field
        if (value > spdz.torch_max_value).all(): # TODO: value per value
            return value - spdz.torch_field
        else:
            return value