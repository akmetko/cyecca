from __future__ import annotations

import numpy as np
import numpy.typing as npt
from numpy import floating

from beartype import beartype
from beartype.typing import List

from cyecca.lie.base import *
from cyecca.lie.group_so3 import *
from cyecca.symbolic import SERIES


__all__ = ["se23", "SE23EulerB321", "SE23Quat", "SE23Mrp"]


@beartype
class SE23LieAlgebra(LieAlgebra):
    def __init__(self):
        super().__init__(n_param=9, matrix_shape=(5, 5))

    def bracket(self, left: LieAlgebraElement, right: LieAlgebraElement):
        assert self == left.algebra
        assert self == right.algebra
        c = left.to_Matrix() @ right.to_Matrix() - right.to_Matrix() @ left.to_Matrix()
        return self.elem(
            param=np.array(
                [
                    c[0, 4],
                    c[1, 4],
                    c[2, 4],
                    c[0, 3],
                    c[1, 3],
                    c[2, 3],
                    c[2, 1],
                    c[0, 2],
                    c[1, 0],
                ]
            )
        )

    def addition(
        self, left: LieAlgebraElement, right: LieAlgebraElement
    ) -> LieAlgebraElement:
        assert self == left.algebra
        assert self == right.algebra
        return self.elem(param=left.param + right.param)

    def scalar_multiplication(
        self, left: SCALAR_TYPE, right: LieAlgebraElement
    ) -> LieAlgebraElement:
        assert self == right.algebra
        return self.elem(param=left * right.param)

    def adjoint(self, arg: LieAlgebraElement):
        assert self == arg.algebra
        a = arg.param[3:6]
        ax = np.array([[0, -p[2], p[1]], [p[2], 0, -p[0]], [-p[1], p[0], 0]])
        v = arg.param[0:3]
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        w = so3.elem(arg.param[6:]).to_Matrix()
        return np.block([[w, vx], [ca.SX(3, 3), w]])

    def to_Matrix(self, arg: LieAlgebraElement) -> npt.NDArray[np.floating]:
        assert self == arg.algebra
        Omega = so3.elem(arg.param[6:]).to_Matrix()
        p = arg.param[:3].reshape(3, 1)
        v = arg.param[3:6].reshape(3, 1)
        Z15 = ca.SX(1, 5)
        return np.block([[Omega, v, p], [Z15]])

    def from_Matrix(self, arg: ca.SX) -> LieAlgebraElement:
        assert arg.shape == self.matrix_shape
        raise NotImplementedError("")

    def wedge(self, arg: npt.NDArray[np.floating]) -> LieAlgebraElement:
        return self.elem(param=arg)

    def vee(self, arg: LieAlgebraElement) -> npt.NDArray[np.floating]:
        assert self == arg.algebra
        return arg.param


@beartype
class SE23LieGroup(LieGroup):
    def __init__(self, SO3: SO3LieGroup):
        self.SO3 = SO3
        super().__init__(algebra=se23, n_param=10, matrix_shape=(5, 5))

    def product(self, left: LieGroupElement, right: LieGroupElement):
        assert self == left.group
        assert self == right.group
        R = self.SO3.elem(left.param[3:]).to_Matrix()
        v = R @ right.param[:3] + left.param[:3]
        theta = (self.SO3.elem(left.param[3:]) * self.SO3.elem(right.param[3:])).param
        x = np.block([v, theta])
        return self.elem(param=x)

    def inverse(self, arg):
        assert self == arg.group
        v = arg.param[:3]
        theta = arg.param[3:]
        theta_inv = self.SO3.elem(param=theta).inverse()
        R = self.SO3.elem(param=theta).to_Matrix()
        p = -R.T @ v
        return self.elem(param=np.block([p, theta_inv.param]))

    def identity(self) -> LieGroupElement:
        return self.elem(ca.SX(self.n_param, 1))

    def adjoint(self, arg: LieGroupElement):
        assert self == arg.group
        v = arg.param[:3]
        vx = so3.elem(param=v).to_Matrix()
        R = self.SO3.elem(param=arg.param[3:]).to_Matrix()
        return np.block([[R, vx @ R], [ca.SX(3, 3), R]])

    def exp(self, arg: LieAlgebraElement) -> LieGroupElement:
        assert self.algebra == arg.algebra
        v = arg.param
        omega_so3 = self.SO3.algebra.elem(
            v[3:]
        )  # grab only rotation terms for so3 uses ##corrected to v_so3 = v[3:6]
        omega_matrix = omega_so3.to_Matrix()  # matrix for so3
        omega = np.linalg.norm(
            v[3:]
        )  # theta term using norm for sqrt(theta1**2+theta2**2+theta3**2)
        theta = omega_so3.exp(self.SO3).param

        # translational components u
        u = np.array([v[0], v[1], v[2]])

        C1 = SERIES["sin(x)/x"]
        C2 = SERIES["(1 - cos(x))/x^2"]
        C = np.where(
            np.abs(omega) < 1e-7,
            1 / 6 - omega**2 / 120 + omega**4 / 5040,
            (1 - C1) / omega**2,
        )

        V = np.eye(3) + C2 * omega_matrix + C * omega_matrix @ omega_matrix

        return self.elem(np.block([V @ u, theta]))

    def log(self, arg: LieGroupElement) -> LieAlgebraElement:
        assert self == arg.group
        X = arg.to_Matrix()
        angle = arg.param[3:]
        R = X[0:3, 0:3]  # get the SO3 Lie group matrix
        theta = np.arccos((np.trace(R) - 1) / 2)
        angle_so3 = self.SO3.elem(angle).log()
        wSkew = angle_so3.to_Matrix()
        C1 = SERIES["sin(x)/x"]
        C2 = SERIES["(1 - cos(x))/x^2"]
        V_inv = (
            np.eye(3)
            - wSkew / 2
            + (1 / theta**2) * (1 - C1 / (2 * C2)) * wSkew @ wSkew
        )

        t = X[0:3, 3]
        uInv = V_inv @ t
        return self.algebra.elem(np.block([uInv, angle_so3.param]))

    def to_Matrix(self, arg: LieGroupElement) -> npt.NDArray[np.floating]:
        assert self == arg.group
        R = self.SO3.elem(arg.param[3:]).to_Matrix()
        t = arg.param[:3].reshape(3, 1)
        Z13 = ca.SX(1, 3)
        I1 = ca.SX.eye(1)
        return np.block(
            [
                [R, t],
                [Z13, I1],
            ]
        )

    def from_Matrix(self, arg: ca.SX) -> LieGroupElement:
        assert arg.shape == self.matrix_shape
        raise NotImplementedError("")


se23 = SE23LieAlgebra()
SE23Mrp = SE23LieGroup(SO3=SO3Mrp)
SE23Quat = SE23LieGroup(SO3=SO3Quat)
SE23EulerB321 = SE23LieGroup(SO3=SO3EulerB321)
