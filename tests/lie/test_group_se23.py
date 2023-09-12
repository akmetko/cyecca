from ..common import *

from cyecca.lie.group_se23 import *


class Test_LieGroupSE23Mrp(ProfiledTestCase):
    def setUp(self):
        super().setUp()
        self.v1 = ca.DM([1.0, 2.0, 3.0, 1.0, 2.0, 3.0, 0.0, 0.0, 0.0])
        self.v2 = ca.DM([1.0, 2.0, 3.0, 1.0, 2.0, 3.0, 1.0, 0.0, 0.0])

    def test_ctor(self):
        SE23Mrp.elem(param=self.v1)

    def test_bad_operations(self):
        G1 = SE23Mrp.elem(self.v1)
        G2 = SE23Mrp.elem(self.v2)
        s = 1
        with self.assertRaises(TypeError):
            G1 + G2
        with self.assertRaises(TypeError):
            G1 - G2
        with self.assertRaises(TypeError):
            G1 @ G2
        with self.assertRaises(TypeError):
            s * G2

    def test_product(self):
        v3 = self.v1 + self.v2
        G1 = SE23Mrp.elem(self.v1)
        G2 = SE23Mrp.elem(self.v2)
        G3 = G1 * G2

    def test_identity(self):
        G1 = SE23Mrp.elem(self.v1)
        G2 = G1 * SE23Mrp.identity()
        self.assertTrue(SX_close(G1.param, G2.param))

    def test_to_Matrix(self):
        G1 = SE23Mrp.elem(self.v1)
        X = G1.to_Matrix()

    def test_inverse(self):
        G1 = SE23Mrp.elem(self.v1)
        self.assertTrue(SX_close((G1 * G1.inverse()).param, SE23Mrp.identity().param))

    def test_exp(self):
        g1 = SE23Mrp.algebra.elem(self.v1)
        g1.exp(SE23Mrp)

    @unittest.skip
    def test_log(self):
        G1 = SE23Mrp.elem(self.v1)
        G1.log()

    @unittest.skip
    def test_exp_log(self):
        G1 = SE23Mrp.elem(self.v1)
        G2 = G1.log().exp(SE23Mrp)
        print(G1, G2)
        self.assertTrue(G1 == G2)

    def test_print_group(self):
        print(SE23Mrp)
