from __future__ import annotations

from beartype import beartype
from beartype.typing import List

import casadi as ca

from cyecca.lie.base import *
from cyecca.lie.group_rn import *
from cyecca.lie.group_rn import R3LieAlgebraElement
from cyecca.lie.group_so3 import *
from cyecca.lie.group_so3 import SO3LieGroupElement, SO3LieAlgebraElement
from cyecca.symbolic import SERIES


__all__ = ["se23", "SE23Quat", "SE23Mrp"]


@beartype
class SE23LieAlgebra(LieAlgebra):
    def __init__(self):
        super().__init__(n_param=9, matrix_shape=(5, 5))

    def elem(self, param: PARAM_TYPE) -> SE23LieAlgebraElement:
        return SE23LieAlgebraElement(algebra=self, param=param)

    def bracket(self, left: SE23LieAlgebraElement, right: SE23LieAlgebraElement):
        c = left.to_Matrix() @ right.to_Matrix() - right.to_Matrix() @ left.to_Matrix()
        return self.elem(
            param=ca.vertcat(
                c[0, 4],
                c[1, 4],
                c[2, 4],
                c[0, 3],
                c[1, 3],
                c[2, 3],
                c[2, 1],
                c[0, 2],
                c[1, 0],
            )
        )

    def addition(
        self, left: SE23LieAlgebraElement, right: SE23LieAlgebraElement
    ) -> SE23LieAlgebraElement:
        return self.elem(param=left.param + right.param)

    def scalar_multiplication(
        self, left: SCALAR_TYPE, right: SE23LieAlgebraElement
    ) -> SE23LieAlgebraElement:
        return self.elem(param=left * right.param)

    def adjoint(self, arg: SE23LieAlgebraElement):
        a_b = arg.a_b
        v_b = arg.v_b

        a_b_x = so3.wedge(a_b.param)
        v_b_x = so3.wedge(v_b.param)

        Omega = arg.Omega.to_Matrix()
        # TODO, check this
        return ca.vertcat(
            ca.horzcat(Omega, a_b_x, v_b_x),
            ca.horzcat(ca.SX(3, 3), Omega, ca.SX(3, 3)),
            ca.horzcat(ca.SX(3, 3), ca.SX(3, 3), Omega),
        )

    def to_Matrix(self, arg: SE23LieAlgebraElement) -> ca.SX:
        return ca.vertcat(
            ca.horzcat(arg.Omega.to_Matrix(), arg.a_b.param, arg.v_b.param), ca.SX(2, 5)
        )

    def from_Matrix(self, arg: ca.SX) -> SE23LieAlgebraElement:
        raise NotImplementedError("")


@beartype
class SE23LieAlgebraElement(LieAlgebraElement):
    """
    This is an SE23 Lie algebra elem
    """

    def __init__(self, algebra: SE23LieAlgebra, param: PARAM_TYPE):
        super().__init__(algebra, param)

    @property
    def a_b(self) -> R3LieAlgebraElement:
        return r3.elem(self.param[:3])

    @property
    def v_b(self) -> R3LieAlgebraElement:
        return r3.elem(self.param[3:6])

    @property
    def Omega(self) -> SO3LieAlgebraElement:
        return so3.elem(self.param[6:])


@beartype
class SE23LieGroup(LieGroup):
    def __init__(self, SO3: SO3LieGroup):
        self.SO3 = SO3
        super().__init__(algebra=se23, n_param=SO3.n_param + 6, matrix_shape=(5, 5))

    def elem(self, param: PARAM_TYPE) -> SE23LieGroupElement:
        return SE23LieGroupElement(group=self, param=param)

    def product(self, left: SE23LieGroupElement, right: SE23LieGroupElement):
        p = left.p + left.R @ right.p
        v = left.v + left.R @ right.v
        R = left.R * right.R
        return self.elem(param=ca.vertcat(p.param, v.param, R.param))

    def inverse(self, arg):
        R_inv = arg.R.inverse()
        p_inv = -(R_inv @ arg.p)
        v_inv = -(R_inv @ arg.v)
        return self.elem(param=ca.vertcat(p_inv.param, v_inv.param, R_inv.param))

    def identity(self) -> SE23LieGroupElement:
        p = R3.identity()
        v = R3.identity()
        R = self.SO3.identity()
        return self.elem(param=ca.vertcat(p.param, v.param, R.param))

    def adjoint(self, arg: SE23LieGroupElement):
        R = arg.R.to_Matrix()
        vx = so3.wedge(arg.v).to_Matrix()
        return np.block([[R, vx @ R], [ca.SX(3, 3), R]])

    def exp(self, arg: SE23LieAlgebraElement) -> SE23LieGroupElement:
        Omega = arg.to_Matrix()
        Omega2 = Omega @ Omega
        Omega3 = Omega2 @ Omega

        theta = ca.norm_2(arg.Omega.param)
        C1 = SERIES["(1 - cos(x))/x^2"](theta)
        C2 = SERIES["(x - sin(x))/x^3"](theta)
        return self.from_Matrix(ca.SX.eye(5) + C1 * Omega2 + C2 * Omega3)

    def log(self, arg: SE23LieGroupElement) -> SE23LieAlgebraElement:
        X = arg.to_Matrix()
        angle = arg.param[3:]
        R = X[0:3, 0:3]  # get the SO3 Lie groupbase matrix
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

    def to_Matrix(self, arg: SE23LieGroupElement) -> ca.SX:
        return ca.vertcat(
            ca.horzcat(arg.R.to_Matrix(), arg.v.param, arg.p.param),
            ca.horzcat(ca.SX(2, 3), ca.SX.eye(2)),
        )

    def from_Matrix(self, arg: ca.SX) -> SE23LieGroupElement:
        R = SO3Mrp.from_Matrix(arg[:3, :3])
        v = r3.elem(arg[:3, 3])
        p = r3.elem(arg[:3, 4])
        return self.elem(ca.vertcat(R.param, v.param, p.param))


@beartype
class SE23LieGroupElement(LieGroupElement):
    """
    This is an SE23 Lie group elem, not necessarily represented as a matrix
    """

    def __init__(self, group: SE23LieGroup, param: PARAM_TYPE):
        super().__init__(group, param)

    @property
    def p(self) -> R3LieAlgebraElement:
        return r3.elem(self.param[:3])

    @property
    def v(self) -> R3LieAlgebraElement:
        return r3.elem(self.param[3:6])

    @property
    def R(self) -> SO3LieGroupElement:
        return self.group.SO3.elem(self.param[6:])


se23 = SE23LieAlgebra()
SE23Mrp = SE23LieGroup(SO3=SO3Mrp)
SE23Quat = SE23LieGroup(SO3=SO3Quat)
