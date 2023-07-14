from __future__ import annotations

import numpy as np
import numpy.typing as npt
from numpy import floating

from beartype import beartype
from beartype.typing import List

from ._base import LieAlgebra, LieAlgebraElement, LieGroup, LieGroupElement
from ._so2 import SO2, so2


@beartype
class SE2LieAlgebra(LieAlgebra):
    def __init__(self):
        super().__init__(n_param=3, matrix_shape=(3, 3))

    def bracket(
        self, left: LieAlgebraElement, right: LieAlgebraElement
    ) -> LieAlgebraElement:
        assert self == left.algebra
        assert self == right.algebra
        c = left.to_matrix()@right.to_matrix() - right.to_matrix()@left.to_matrix()
        return self.element(param=np.array([c[0, 2], c[1, 2], c[1, 0]]))

    def addition(
        self, left: LieAlgebraElement, right: LieAlgebraElement
    ) -> LieAlgebraElement:
        assert self == left.algebra
        assert self == right.algebra
        return self.element(param=left.param + right.param)

    def scalar_multipication(self, left : Real, right: LieAlgebraElement) -> LieAlgebraElement:
        assert self == right.algebra
        return self.element(param=left * right.param)

    def adjoint(self, left: LieAlgebraElement) -> npt.NDArray[np.floating]:
        assert self == left.algebra
        x, y, theta = left.param
        return np.array([
            [0, -theta, y],
            [theta, 0, -x],
            [0, 0, 0]
        ])

    def to_matrix(self, left: LieAlgebraElement) -> npt.NDArray[np.floating]:
        assert self == left.algebra
        Omega = so2.element(left.param[2:]).to_matrix()
        v = left.param[:2].reshape(2,1)
        Z13 = np.zeros(3)
        return np.block([
            [Omega, v],
            [Z13]
        ])
    
    def wedge(self, left: npt.NDArray[np.floating]) -> LieAlgebraElement:
        self = SE2LieAlgebra()
        return self.element(param=left)
    
    def vee(self, left: LieAlgebraElement) -> npt.NDArray[np.floating]:
        assert self == left.algebra
        return left.param


@beartype
class SE2LieGroup(LieGroup):
    def __init__(self):
        super().__init__(algebra=se2, n_param=3, matrix_shape=(3, 3))

    def product(self, left: LieGroupElement, right: LieGroupElement):
        assert self == left.group
        assert self == right.group
        R = SO2.element(left.param[2:]).to_matrix()
        v = (R@right.param[:2]+left.param[:2])
        x = np.block([v, left.param[2:]+right.param[2:]])
        return self.element(param=x)

    def inverse(self, left: LieGroupElement) -> LieGroupElement:
        assert self == left.group
        v = left.param[:2]
        theta = left.param[2:]
        R = SO2.element(param=theta).to_matrix()
        p = -R.T@v
        return self.element(param=np.array([p[0], p[1], -theta[0]]))

    def identity(self) -> LieGroupElement:
        return self.element(param=np.zeros(self.n_param))

    def adjoint(self, left: LieGroupElement):
        assert self == left.group
        v = np.array([left.param[1], -left.param[0]])
        theta = SO2.element(param=left.param[2:])
        return np.block([[theta.to_matrix(), v.reshape(2,1)],
                         [np.zeros((1,2)), 1]])

    def exp(self, left: LieAlgebraElement) -> LieGroupElement:
        assert self.algebra == left.algebra
        theta = left.param[2]
        sin_th = np.sin(theta)
        cos_th = np.cos(theta)
        a = sin_th / theta
        b = (1 - cos_th) / theta
        V = np.array([
            [a, -b],
            [b, a]])
        v = V @ left.param[:2]
        return self.element(np.array([v[0], v[1], theta]))

    def log(self, left: LieGroupElement) -> LieAlgebraElement:
        assert self == left.group
        v = left.param[:2]
        theta = left.param[2]
        with np.errstate(divide='ignore',invalid='ignore'):
            a = np.where(np.abs(theta) < 1e-3, 1 - theta**2/6 + theta**4/120, np.sin(theta)/theta)
            b = np.where(np.abs(theta) < 1e-3, theta/2 - theta**3/24 + theta**5/720, (1 - np.cos(theta))/theta)
        V_inv = np.array([
            [a, b],
            [-b, a]
        ])/(a**2 + b**2)
        p = V_inv@v
        return self.algebra.element(np.array([p[0], p[1], theta]))

    def to_matrix(self, left: LieGroupElement) -> npt.NDArray[np.floating]:
        assert self == left.group
        R = SO2.element(left.param[2:]).to_matrix()
        t = left.param[:2].reshape(2,1)
        Z12 = np.zeros(2)
        I1 = np.eye(1)
        return np.block([
            [R, t],
            [Z12, I1],
        ])


se2 = SE2LieAlgebra()
SE2 = SE2LieGroup()
