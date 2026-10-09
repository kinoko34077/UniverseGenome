"""D7 #187 frozen receiver microcase/operator-stage classification safety tests."""
import unittest
from research import d7_receiver_contrast_187 as d7


class D7ReceiverTests(unittest.TestCase):
    def test_six_physical_stages_and_transition_classification(self):
        self.assertEqual(d7.STAGES,(
            "before_write","after_write","before_transfer","after_transfer","after_decay","end"
        ))
        self.assertEqual(d7.stage_transitions(False,[False,False,False,True,True,True]),
                         [("after_transfer","appear")])
        self.assertEqual(d7.stage_transitions(True,[True,False,False,False,False,False]),
                         [("after_write","disappear")])
        self.assertEqual(d7.stage_transitions(True,[True,False,True,True,True,True]),
                         [("after_write","disappear"),("before_transfer","appear")])
        with self.assertRaises(ValueError):
            d7.stage_transitions(False,[False])

    def test_prior_real_life_epoch_constraints_are_fixed(self):
        self.assertEqual(d7.PRIMARY,575)
        self.assertEqual(d7.SENTINEL,545)
        self.assertEqual((d7.DONOR,d7.RECIPIENT),(15,6))
        self.assertEqual((d7.TRANSFER_GEN,d7.DONOR_FREE_GEN),(61,724))
        self.assertEqual(d7.PROTOCOL["recipient"]["epoch"],0)
        self.assertEqual(d7.PROTOCOL["recipient"]["donor_epoch"],0)
        self.assertEqual(d7.HORIZON,1000)

    def test_excludes_all_other_seeds_and_promotion(self):
        for seed in [0,166,555,560,582,1024,4096]:
            with self.assertRaises(ValueError):
                d7.validate_seed(seed)
        for seed in [575,545]:
            d7.validate_seed(seed)
        self.assertFalse(d7.PROTOCOL["learning_claim"])
        self.assertIn("NOT independently confirmatory",d7.PROTOCOL["data_role"])
        self.assertEqual(d7.R2_DIGEST,
                         "3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543")

    def test_frozen_roster_contains_both_target_roles(self):
        f=d7.load_frozen()
        self.assertIn(d7.PRIMARY,f["positive_seeds"])
        self.assertIn(d7.SENTINEL,f["negative_seeds"])
        self.assertFalse(set((d7.PRIMARY,d7.SENTINEL))&set(range(0,544)))


if __name__=="__main__":
    unittest.main()
