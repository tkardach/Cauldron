"""Deterministic tests for the WaterDropletEffect.

Every test below builds the effect from explicit physical parameters, so the
simulation state (and therefore the value of any LED in the grid) is fully
reproducible for a given elapsed time.
"""

import math
import random
import unittest

import numpy as np

from cauldron.core.led_effect import (
    BoundaryCondition,
    TimeMode,
    WaterDropletEffect,
)
from cauldron.core.led_strip import MockStrip, RgbArrayStrip


# Physical parameters shared by the deterministic tests.
LED_DENSITY = 60.0  # LEDs per meter
NUM_LEDS = 20  # LEDs per strip
NUM_STRIPS = 5
STRIP_LENGTH = NUM_LEDS / LED_DENSITY  # meters
DAMPING = 0.9  # amplitude retained per second
WAVE_SPEED = 0.35  # meters per second
DROP_AMPLITUDE = 0.01  # meters
DROP_RADIUS = 0.05  # meters


def build_effect(
    num_strips: int = NUM_STRIPS,
    num_leds: int = NUM_LEDS,
    boundary_conditions=BoundaryCondition.REFLECTIVE,
    drop_frequency: float = 0.0,
    damping: float = DAMPING,
    drop_amplitude: float = DROP_AMPLITUDE,
    drop_radius: float = DROP_RADIUS,
    wave_speed: float = WAVE_SPEED,
    seed: int = 42,
    **kwargs,
) -> WaterDropletEffect:
    """Builds a WaterDropletEffect with fully specified physical inputs."""
    strips = [MockStrip(num_leds) for _ in range(num_strips)]
    return WaterDropletEffect(
        strips,
        led_strip_length=num_leds / LED_DENSITY,
        led_density=LED_DENSITY,
        damping=damping,
        wave_speed=wave_speed,
        boundary_conditions=boundary_conditions,
        drop_amplitude=drop_amplitude,
        drop_radius=drop_radius,
        drop_frequency=drop_frequency,
        seed=seed,
        **kwargs,
    )


class TestWaterDropletGeometry(unittest.TestCase):
    """Grid layout/geometry derived from the physical characteristics."""

    def test_grid_shape_matches_strip_grid(self):
        effect = build_effect()
        self.assertEqual(effect.grid_shape, (NUM_STRIPS, NUM_LEDS))
        self.assertEqual(len(effect.led_strips), NUM_STRIPS)
        self.assertEqual(effect.displacement.shape, (NUM_STRIPS, NUM_LEDS))
        self.assertEqual(effect.brightness_grid.shape, (NUM_STRIPS, NUM_LEDS))

    def test_single_strip_is_accepted_and_is_a_center_slice(self):
        """A single strip is a horizontal slice through the drop center."""
        strip = MockStrip(NUM_LEDS)
        effect = WaterDropletEffect(
            strip,
            led_strip_length=STRIP_LENGTH,
            led_density=LED_DENSITY,
            drop_frequency=0.0,
            drop_amplitude=DROP_AMPLITUDE,
            drop_radius=DROP_RADIUS,
        )
        self.assertEqual(effect.grid_shape, (1, NUM_LEDS))
        # The droplet lands on the strip itself, so the LED closest to the
        # impact reaches the full drop amplitude.
        effect.add_drop(x=(9 + 0.5) / LED_DENSITY)
        self.assertAlmostEqual(
            effect.get_displacement(0, 9), -DROP_AMPLITUDE, places=12
        )
        self.assertAlmostEqual(effect.get_brightness(0, 9), 1.0, places=12)

    def test_led_pitch_and_time_step_are_stable(self):
        effect = build_effect()
        dx = 1.0 / LED_DENSITY
        max_dt = 1.0 / (WAVE_SPEED * math.sqrt(2.0 / dx**2))
        self.assertAlmostEqual(effect.time_step, 0.5 * max_dt, places=12)
        self.assertLess(effect.time_step, max_dt)

    def test_custom_stable_time_step_is_honoured(self):
        effect = build_effect(time_step=0.005)
        self.assertAlmostEqual(effect.time_step, 0.005, places=12)
        effect.update(0.1)
        self.assertAlmostEqual(effect.simulation_time, 0.1, places=9)

    def test_unstable_time_step_is_clamped(self):
        effect = build_effect(time_step=10.0)
        dx = 1.0 / LED_DENSITY
        max_dt = 1.0 / (WAVE_SPEED * math.sqrt(2.0 / dx**2))
        self.assertAlmostEqual(effect.time_step, max_dt, places=12)

    def test_invalid_parameters_are_rejected(self):
        with self.assertRaises(AssertionError):
            build_effect(damping=1.5)
        with self.assertRaises(AssertionError):
            build_effect(wave_speed=0)
        with self.assertRaises(AssertionError):
            build_effect(drop_amplitude=0)
        with self.assertRaises(AssertionError):
            build_effect(drop_radius=-1)
        with self.assertRaises(AssertionError):
            # Strips of different lengths cannot form a grid.
            WaterDropletEffect([MockStrip(10), MockStrip(11)])
        with self.assertRaises(ValueError):
            build_effect(boundary_conditions="bouncy")

    def test_time_mode_parsing(self):
        self.assertEqual(TimeMode.parse("Delta"), TimeMode.DELTA)
        self.assertEqual(
            TimeMode.parse(TimeMode.ABSOLUTE), TimeMode.ABSOLUTE
        )
        with self.assertRaises(ValueError):
            TimeMode.parse("frames")
        effect = build_effect(time_mode="delta")
        effect.update(0.5)
        effect.update(0.5)
        self.assertAlmostEqual(
            effect.simulation_time, 1.0, delta=effect.time_step
        )

    def test_inconsistent_physical_length_warns(self):
        with self.assertLogs(level="WARNING") as logs:
            WaterDropletEffect(
                MockStrip(NUM_LEDS),
                led_strip_length=5.0,  # does not match 20 LEDs at 60 LEDs/m
                led_density=LED_DENSITY,
                drop_frequency=0.0,
            )
        self.assertIn("led_strip_length", logs.output[0])

    def test_boundary_condition_parsing(self):
        self.assertEqual(
            BoundaryCondition.parse("Reflective"), BoundaryCondition.REFLECTIVE
        )
        self.assertEqual(
            BoundaryCondition.parse("disappear"), BoundaryCondition.DISAPPEAR
        )
        self.assertEqual(
            BoundaryCondition.parse(BoundaryCondition.WRAPPED),
            BoundaryCondition.WRAPPED,
        )
        effect = build_effect(boundary_conditions="Wrapped")
        self.assertEqual(effect.boundary_conditions, BoundaryCondition.WRAPPED)


class TestWaterDropletDropShape(unittest.TestCase):
    """The droplet impact profile in physical units."""

    def test_impact_matches_analytic_raised_cosine(self):
        effect = build_effect()
        drop_x = 10 / LED_DENSITY
        drop_y = 2.5 / LED_DENSITY
        effect.add_drop(x=drop_x, y=drop_y)
        effect.update(0.0)

        # LED (2, 10) sits 0.5 LED (1/120 m) away from the impact center.
        distance = 0.5 / LED_DENSITY
        expected_u = -DROP_AMPLITUDE * 0.5 * (
            1.0 + math.cos(math.pi * distance / DROP_RADIUS)
        )
        self.assertAlmostEqual(
            effect.get_displacement(2, 10), expected_u, places=12
        )
        self.assertAlmostEqual(
            effect.get_brightness(2, 10), abs(expected_u) / DROP_AMPLITUDE, 12
        )
        # Brightness is derived from u: base + brightness * (crest - base).
        np.testing.assert_array_equal(
            effect.get_pixel(2, 10),
            np.array([0, 119, 238]),
        )
        # LEDs outside of the splash radius are untouched.
        self.assertEqual(effect.get_displacement(2, 19), 0.0)
        np.testing.assert_array_equal(
            effect.get_pixel(2, 19), np.array([0, 0, 0])
        )

    def test_drop_radius_limits_the_splash_zone(self):
        effect = build_effect(drop_radius=0.02)
        effect.add_drop(x=10 / LED_DENSITY, y=2.5 / LED_DENSITY)
        effect.update(0.0)
        splashed = np.abs(effect.displacement) > 0
        # A 2cm radius at 60 LEDs/m only wets ~1.2 LEDs around the impact.
        self.assertTrue(splashed[2, 9] and splashed[2, 10])
        self.assertFalse(splashed[2, 7])
        self.assertFalse(splashed[0, 10])

    def test_drop_amplitude_scales_the_ripple(self):
        """A heavier drop is brighter and rings out longer."""
        small = build_effect(drop_amplitude=0.002)
        large = build_effect(drop_amplitude=0.01)
        for effect in (small, large):
            effect.add_drop(x=10 / LED_DENSITY, y=2.5 / LED_DENSITY)
            effect.update(0.4)
        # The wave equation is linear, so u scales exactly with the amplitude.
        np.testing.assert_allclose(
            large.displacement, small.displacement * 5.0, rtol=1e-9, atol=1e-15
        )
        # ... which makes the heavy drop brighter everywhere.
        self.assertGreater(
            large.brightness_grid.max(), small.brightness_grid.max()
        )
        self.assertGreater(
            np.count_nonzero(large.brightness_grid > 0.05),
            np.count_nonzero(small.brightness_grid > 0.05),
        )


class TestWaterDropletDeterminism(unittest.TestCase):
    """update() must be deterministic for arbitrary time intervals."""

    #: Golden values captured from the fixed step simulation described by
    #: build_effect() with a single droplet at (x=10/60m, y=2.5/60m).
    GOLDEN_T = 0.25
    GOLDEN_LED_VALUES = {
        (2, 10): -0.0025628854949301299,
        (2, 5): -0.0023744217167169348,
        (2, 15): -0.0020907743015405118,
        (0, 0): -5.8629968075616332e-06,
        (4, 19): -5.8629968075616112e-06,
    }
    GOLDEN_PIXELS = {
        (2, 10): [0, 33, 65],
        (2, 5): [0, 30, 61],
        (2, 15): [0, 27, 53],
    }

    def _golden_effect(self) -> WaterDropletEffect:
        effect = build_effect()
        effect.add_drop(x=10 / LED_DENSITY, y=2.5 / LED_DENSITY)
        return effect

    def _assert_golden(self, effect: WaterDropletEffect):
        for (row, col), expected in self.GOLDEN_LED_VALUES.items():
            self.assertAlmostEqual(
                effect.get_displacement(row, col), expected, places=12
            )
        for (row, col), expected in self.GOLDEN_PIXELS.items():
            np.testing.assert_array_equal(
                effect.get_pixel(row, col), np.array(expected)
            )

    def test_specific_led_values_for_a_given_time_delta(self):
        """The value of a specific LED is known for a given time delta."""
        effect = self._golden_effect()
        effect.update(self.GOLDEN_T)
        self._assert_golden(effect)

    def test_same_state_for_arbitrary_frame_intervals(self):
        """Irregular frame intervals converge on the same state."""
        single_shot = self._golden_effect()
        single_shot.update(self.GOLDEN_T)

        fine = self._golden_effect()
        for step in range(1, 251):
            fine.update(step * (self.GOLDEN_T / 250.0))
        np.testing.assert_array_equal(
            fine.displacement, single_shot.displacement
        )

        jittery = self._golden_effect()
        rng = random.Random(1234)
        t = 0.0
        while t < self.GOLDEN_T:
            t = min(self.GOLDEN_T, t + rng.uniform(0.0005, 0.05))
            jittery.update(t)
        np.testing.assert_array_equal(
            jittery.displacement, single_shot.displacement
        )
        self._assert_golden(jittery)

    def test_delta_time_mode_matches_absolute_time_mode(self):
        """TimeMode.DELTA accumulates arbitrary deltas deterministically."""
        absolute = self._golden_effect()
        absolute.update(self.GOLDEN_T)

        strips = [MockStrip(NUM_LEDS) for _ in range(NUM_STRIPS)]
        delta = WaterDropletEffect(
            strips,
            led_strip_length=STRIP_LENGTH,
            led_density=LED_DENSITY,
            damping=DAMPING,
            wave_speed=WAVE_SPEED,
            drop_amplitude=DROP_AMPLITUDE,
            drop_radius=DROP_RADIUS,
            drop_frequency=0.0,
            seed=42,
            time_mode=TimeMode.DELTA,
        )
        delta.add_drop(x=10 / LED_DENSITY, y=2.5 / LED_DENSITY)
        for _ in range(25):
            delta.update(self.GOLDEN_T / 25.0)
        np.testing.assert_array_equal(
            delta.displacement, absolute.displacement
        )
        self._assert_golden(delta)

    def test_two_effects_with_identical_inputs_match(self):
        first, second = build_effect(drop_frequency=2.0), build_effect(
            drop_frequency=2.0
        )
        for t in (0.1, 0.37, 1.0, 2.5):
            first.update(t)
            second.update(t)
        np.testing.assert_array_equal(first.displacement, second.displacement)
        np.testing.assert_array_equal(
            first.led_strips[0].get_pixels(), second.led_strips[0].get_pixels()
        )

    def test_rewinding_time_replays_deterministically(self):
        """Scheduled droplets are replayed when time moves backwards."""
        forward = build_effect(drop_frequency=2.0)
        forward.update(self.GOLDEN_T)
        expected = forward.displacement

        rewound = build_effect(drop_frequency=2.0)
        rewound.update(1.5)
        rewound.update(self.GOLDEN_T)  # jump back in time
        np.testing.assert_array_equal(rewound.displacement, expected)
        self.assertEqual(rewound.drop_count, forward.drop_count)

    def test_reset_restores_the_initial_state(self):
        effect = build_effect(drop_frequency=2.0)
        initial = effect.displacement
        effect.update(1.0)
        self.assertGreater(np.abs(effect.displacement).sum(), 0.0)
        effect.reset()
        np.testing.assert_array_equal(effect.displacement, initial)
        self.assertEqual(effect.simulation_time, 0.0)
        effect.update(1.0)
        self.assertAlmostEqual(effect.simulation_time, 1.0, delta=effect.time_step)


class TestWaterDropletPhysics(unittest.TestCase):
    """Validates the numerical damped wave equation approximation."""

    def test_matches_analytic_damped_wave_solution(self):
        """A single spatial mode must decay like exp(-gamma * t)."""
        num_leds = 120
        density = 120.0
        damping = 0.5
        wave_speed = 1.0
        strip = MockStrip(num_leds)
        effect = WaterDropletEffect(
            strip,
            led_strip_length=num_leds / density,
            led_density=density,
            damping=damping,
            wave_speed=wave_speed,
            boundary_conditions=BoundaryCondition.WRAPPED,
            drop_frequency=0.0,
        )
        x = (np.arange(num_leds) + 0.5) / density
        k = 2.0 * math.pi * 2.0  # two full periods across the strip
        amplitude = 0.01
        mode = amplitude * np.cos(k * x)[None, :]
        # Seed a standing wave at rest (u[n] == u[n-1]).
        effect._u = mode.copy()
        effect._u_prev = mode.copy()

        gamma = -math.log(damping)
        omega = wave_speed * k
        omega_d = math.sqrt(omega**2 - gamma**2)
        for t in (0.25, 0.5, 1.0, 2.0):
            effect.update(t)
            simulated = effect.displacement[0]
            measured = np.sum(simulated * np.cos(k * x)) / np.sum(
                np.cos(k * x) ** 2
            )
            analytic = (
                amplitude
                * math.exp(-gamma * t)
                * (
                    math.cos(omega_d * t)
                    + (gamma / omega_d) * math.sin(omega_d * t)
                )
            )
            self.assertAlmostEqual(measured, analytic, delta=5e-6)

    def test_damping_controls_how_long_the_ripple_rings_out(self):
        thin = build_effect(damping=0.98)  # water: rings for a long time
        thick = build_effect(damping=0.2)  # oil: fizzles out quickly
        for effect in (thin, thick):
            effect.add_drop(x=10 / LED_DENSITY, y=2.5 / LED_DENSITY)
            effect.update(2.0)
        self.assertGreater(
            np.abs(thin.displacement).sum(), np.abs(thick.displacement).sum()
        )
        self.assertLess(thick.brightness_grid.max(), 0.2)

    def test_ripple_travels_at_the_configured_wave_speed(self):
        num_leds = 90
        strip = MockStrip(num_leds)
        wave_speed = 0.35
        radius = 0.02
        effect = WaterDropletEffect(
            strip,
            led_strip_length=num_leds / LED_DENSITY,
            led_density=LED_DENSITY,
            damping=1.0,
            wave_speed=wave_speed,
            drop_frequency=0.0,
            drop_radius=radius,
            drop_amplitude=DROP_AMPLITUDE,
        )
        center_led = 45
        center_x = (center_led + 0.5) / LED_DENSITY
        effect.add_drop(x=center_x)

        for t in (0.4, 0.8):
            effect.update(t)
            u = np.abs(effect.displacement[0])
            # Ignore the exponentially small numerical precursor.
            wet = np.flatnonzero(u > 0.1 * u.max())
            front_led = wet.max()
            front_distance = (front_led + 0.5) / LED_DENSITY - center_x
            expected = radius + wave_speed * effect.simulation_time
            # The wave front travels at c (within a couple of LEDs).
            self.assertAlmostEqual(
                front_distance, expected, delta=2.0 / LED_DENSITY
            )
            # The ripple is symmetric around the impact point.
            self.assertAlmostEqual(
                center_x - (wet.min() + 0.5) / LED_DENSITY,
                front_distance,
                delta=1.0 / LED_DENSITY,
            )


class TestWaterDropletBoundaryConditions(unittest.TestCase):
    """Reflective / Disappear / Wrapped edge behaviour."""

    def _single_strip_effect(self, boundary, num_leds=40):
        strip = MockStrip(num_leds)
        return WaterDropletEffect(
            strip,
            led_strip_length=num_leds / LED_DENSITY,
            led_density=LED_DENSITY,
            damping=1.0,
            wave_speed=WAVE_SPEED,
            boundary_conditions=boundary,
            drop_amplitude=DROP_AMPLITUDE,
            drop_radius=DROP_RADIUS,
            drop_frequency=0.0,
        )

    def test_reflective_boundary_bounces_the_ripple_back(self):
        effect = self._single_strip_effect(BoundaryCondition.REFLECTIVE)
        effect.add_drop(x=20 / LED_DENSITY)
        # The ripple needs ~0.9s to reach the edge.
        effect.update(1.0)
        edge_energy = np.abs(effect.displacement[0, :4]).sum()
        self.assertGreater(edge_energy, 0.001)
        # After bouncing, the wave travels back towards the middle.
        effect.update(1.6)
        self.assertGreater(np.abs(effect.displacement[0, 6:16]).sum(), 0.001)
        # A reflective pool keeps (almost) all of its energy.
        self.assertGreater(np.abs(effect.displacement).sum(), 0.02)

    def test_disappearing_boundary_absorbs_the_ripple(self):
        effect = self._single_strip_effect(BoundaryCondition.DISAPPEAR)
        effect.add_drop(x=20 / LED_DENSITY)
        effect.update(0.5)
        traveling_energy = np.abs(effect.displacement).sum()
        self.assertGreater(traveling_energy, 0.02)
        # Once the ripple hits the edges it is gone for good.
        effect.update(1.5)
        self.assertLess(np.abs(effect.displacement).sum(), 0.1 * traveling_energy)
        self.assertLess(effect.brightness_grid.max(), 0.05)

    def test_wrapped_boundary_reappears_on_the_opposite_edge(self):
        effect = self._single_strip_effect(BoundaryCondition.WRAPPED)
        # Drop close to the right edge; the right-going ripple must reappear
        # on the left edge of the strip.
        effect.add_drop(x=35 / LED_DENSITY)
        self.assertEqual(effect.displacement[0, 0], 0.0)
        effect.update(0.25)
        self.assertGreater(np.abs(effect.displacement[0, :3]).sum(), 1e-5)
        # A reflective strip would still be empty on the left edge.
        reflective = self._single_strip_effect(BoundaryCondition.REFLECTIVE)
        reflective.add_drop(x=35 / LED_DENSITY)
        reflective.update(0.25)
        self.assertLess(np.abs(reflective.displacement[0, :3]).sum(), 1e-9)

    def test_wrapped_grid_wraps_between_strips(self):
        effect = build_effect(
            boundary_conditions=BoundaryCondition.WRAPPED, damping=1.0
        )
        # Drop on the top row: the ripple must wrap onto the bottom row.
        effect.add_drop(x=10 / LED_DENSITY, y=0.5 / LED_DENSITY)
        effect.update(0.2)
        self.assertGreater(np.abs(effect.displacement[-1]).sum(), 1e-6)


class TestWaterDropletStability(unittest.TestCase):
    """The finite difference scheme must never blow up."""

    def test_simulation_stays_bounded_for_every_grid_and_boundary(self):
        for num_strips in (1, 2, 3, 8):
            for num_leds in (2, 3, 60):
                for boundary in BoundaryCondition:
                    with self.subTest(
                        strips=num_strips, leds=num_leds, boundary=boundary
                    ):
                        effect = build_effect(
                            num_strips=num_strips,
                            num_leds=num_leds,
                            boundary_conditions=boundary,
                            drop_frequency=4.0,
                            damping=0.95,
                        )
                        effect.update(3.0)
                        displacement = effect.displacement
                        self.assertTrue(np.isfinite(displacement).all())
                        self.assertLess(np.abs(displacement).max(), 1.0)

    def test_tiny_splash_zone_still_disturbs_the_nearest_led(self):
        effect = build_effect(drop_radius=0.0005)
        effect.add_drop(x=10 / LED_DENSITY, y=2.5 / LED_DENSITY)
        self.assertEqual(np.count_nonzero(effect.displacement), 1)
        effect.update(0.5)
        self.assertTrue(np.isfinite(effect.displacement).all())


class TestWaterDropletSpawning(unittest.TestCase):
    """Deterministic droplet scheduling."""

    def test_drop_frequency_controls_the_number_of_drops(self):
        effect = build_effect(drop_frequency=2.0)
        self.assertEqual(effect.drop_count, 1)  # first drop lands at t = 0
        effect.update(1.0)
        self.assertEqual(effect.drop_count, 2)
        effect.update(2.1)
        self.assertEqual(effect.drop_count, 5)

    def test_no_drops_when_frequency_is_zero(self):
        effect = build_effect(drop_frequency=0.0)
        effect.update(5.0)
        self.assertEqual(effect.drop_count, 0)
        np.testing.assert_array_equal(
            effect.displacement, np.zeros(effect.grid_shape)
        )

    def test_drop_positions_are_seeded_and_reproducible(self):
        first = build_effect(drop_frequency=2.0, seed=42)
        second = build_effect(drop_frequency=2.0, seed=42)
        third = build_effect(drop_frequency=2.0, seed=7)
        for effect in (first, second, third):
            effect.update(2.0)
        self.assertEqual(
            [(d["x"], d["y"]) for d in first._drops],
            [(d["x"], d["y"]) for d in second._drops],
        )
        self.assertNotEqual(
            [(d["x"], d["y"]) for d in first._drops],
            [(d["x"], d["y"]) for d in third._drops],
        )
        # Golden position of the very first droplet for seed 42.
        self.assertAlmostEqual(first._drops[0]["x"], 0.2579853495186544, 12)
        self.assertAlmostEqual(first._drops[0]["y"], 0.03657320331267103, 12)
        # ... and the resulting LED value one second later.
        first.reset()
        first.update(1.0)
        self.assertAlmostEqual(
            first.get_displacement(2, 10), -0.0023003159958754613, places=12
        )
        np.testing.assert_array_equal(
            first.get_pixel(2, 10), np.array([0, 29, 59])
        )

    def test_drops_land_inside_the_grid(self):
        effect = build_effect(drop_frequency=10.0)
        effect.update(3.0)
        self.assertGreater(effect.drop_count, 25)
        for drop in effect._drops:
            self.assertGreaterEqual(drop["x"], 0.0)
            self.assertLessEqual(drop["x"], NUM_LEDS / LED_DENSITY)
            self.assertGreaterEqual(drop["y"], 0.0)
            self.assertLessEqual(drop["y"], NUM_STRIPS / LED_DENSITY)


class TestWaterDropletRendering(unittest.TestCase):
    """LED rendering, colors and LedEffect plumbing."""

    def test_colors_are_interpolated_from_the_displacement(self):
        effect = build_effect(colors=[[10, 0, 0], [10, 200, 100]])
        effect.add_drop(x=(9 + 0.5) / LED_DENSITY, y=2.5 / LED_DENSITY)
        effect.update(0.0)
        brightness = effect.get_brightness(2, 9)
        expected = np.rint(
            np.array([10, 0, 0])
            + brightness * (np.array([10, 200, 100]) - np.array([10, 0, 0]))
        )
        np.testing.assert_array_equal(effect.get_pixel(2, 9), expected)

    def test_input_and_output_colors(self):
        effect = build_effect()
        effect.input_colors = [[1, 2, 3], [4, 5, 6]]
        np.testing.assert_array_equal(effect.input_colors[0], [1, 2, 3])
        np.testing.assert_array_equal(effect.output_colors[1], [4, 5, 6])
        # An empty color list leaves the effect untouched.
        effect.input_colors = []
        np.testing.assert_array_equal(effect.input_colors[0], [1, 2, 3])
        with self.assertRaises(AssertionError):
            effect.input_colors = [[1, 2, 3]]

    def test_every_strip_in_the_grid_is_written_and_shown(self):
        class CountingStrip(RgbArrayStrip):
            def __init__(self, num_pixels):
                super().__init__(num_pixels)
                self.show_count = 0

            def show(self):
                self.show_count += 1

        strips = [CountingStrip(NUM_LEDS) for _ in range(3)]
        effect = WaterDropletEffect(
            strips,
            led_strip_length=STRIP_LENGTH,
            led_density=LED_DENSITY,
            drop_frequency=0.0,
            drop_amplitude=DROP_AMPLITUDE,
            drop_radius=DROP_RADIUS,
        )
        effect.add_drop(x=10 / LED_DENSITY, y=1.5 / LED_DENSITY)
        effect.update(0.1)
        for row, strip in enumerate(strips):
            self.assertEqual(strip.show_count, 1)
            np.testing.assert_array_equal(
                np.asarray(strip.get_pixels(), dtype=int),
                np.clip(
                    np.rint(
                        effect.brightness_grid[row][:, None]
                        * np.array(WaterDropletEffect.DEFAULT_COLORS[1])
                    ),
                    0,
                    255,
                ).astype(int),
            )

        effect.disable_internal_show()
        effect.update(0.2)
        for strip in strips:
            self.assertEqual(strip.show_count, 1)

    def test_brightness_never_leaves_the_unit_interval(self):
        effect = build_effect(drop_frequency=8.0, damping=0.99)
        for t in np.arange(0.0, 3.0, 0.05):
            effect.update(float(t))
            brightness = effect.brightness_grid
            self.assertGreaterEqual(brightness.min(), 0.0)
            self.assertLessEqual(brightness.max(), 1.0)
            pixels = np.asarray(effect.led_strips[0].get_pixels(), dtype=int)
            self.assertGreaterEqual(pixels.min(), 0)
            self.assertLessEqual(pixels.max(), 255)


if __name__ == "__main__":
    unittest.main()
