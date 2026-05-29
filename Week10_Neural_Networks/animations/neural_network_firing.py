"""
CE49X Week 10 — Neural Network Firing Patterns

A simple ManimCE animation that shows how different inputs to a small
feedforward network activate different subsets of hidden neurons,
producing distinct "firing patterns" — the network's internal
fingerprint of each input.

Run with:
    source "../../../activate_manim.sh"
    manim -qm -p neural_network_firing.py FiringPatterns
"""
from manim import *
import numpy as np


# Colour palette — matches the Week 10 lecture notebook.
INPUT_COLOR  = "#4682B4"   # steelblue
FIRE_COLOR   = "#CD5C5C"   # indianred (a neuron's "on" state)
DIM_COLOR    = "#3A3A3A"   # silenced neuron
EDGE_BASE    = "#555555"
SIGNAL_COLOR = "#F5A623"   # amber pulse traveling along an edge


class FiringPatterns(Scene):
    def construct(self):
        self.camera.background_color = "#0D1117"

        self.show_title()
        self.build_network()
        self.show_pattern("A", inputs=[0.9, 0.2, 0.7],
                          firing=[True, False, True, False, True],
                          output_class=0,
                          pattern_str="[ON, off, ON, off, ON]")
        self.reset_network()
        self.show_pattern("B", inputs=[0.2, 0.9, 0.4],
                          firing=[False, True, False, True, False],
                          output_class=1,
                          pattern_str="[off, ON, off, ON, off]",
                          subtitle="(different input → different fingerprint)")
        self.show_emergence()

    # ── Title ─────────────────────────────────────────────────────────
    def show_title(self):
        title = Text("How Neurons Fire", font_size=48, weight=BOLD)
        subtitle = Text(
            "Patterns of firing → the network's fingerprint",
            font_size=26, color=GRAY_B,
        )
        course = Text(
            "CE49X · Week 10 · Neural Networks",
            font_size=20, color=GRAY_C,
        )
        group = VGroup(title, subtitle, course).arrange(DOWN, buff=0.3)
        self.play(Write(title), run_time=0.8)
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=0.5)
        self.play(FadeIn(course, shift=UP * 0.2), run_time=0.4)
        self.wait(1.5)
        self.play(FadeOut(group), run_time=0.5)

    # ── Network skeleton ──────────────────────────────────────────────
    def build_network(self):
        # 3 inputs → 5 hidden → 2 outputs.
        def make_layer(xs, ys):
            return VGroup(*[
                Circle(radius=0.30, color=GRAY_B,
                       fill_opacity=0.3, stroke_width=2).move_to([xs, y, 0])
                for y in ys
            ])

        self.input_nodes  = make_layer(-4.5, [1.5, 0, -1.5])
        self.hidden_nodes = make_layer( 0.0, [2.4, 1.2, 0, -1.2, -2.4])
        self.output_nodes = make_layer( 4.5, [0.8, -0.8])

        # Edges between consecutive layers.
        def connect(layer_a, layer_b):
            edges = VGroup()
            for a in layer_a:
                for b in layer_b:
                    edges.add(Line(a.get_center(), b.get_center(),
                                   stroke_width=1, stroke_color=EDGE_BASE))
            return edges

        self.edges_in_hid  = connect(self.input_nodes,  self.hidden_nodes)
        self.edges_hid_out = connect(self.hidden_nodes, self.output_nodes)

        in_lbl  = Text("inputs", font_size=20, color=GRAY_B
                       ).next_to(self.input_nodes,  DOWN, buff=0.4)
        hid_lbl = Text("hidden (ReLU)", font_size=20, color=GRAY_B
                       ).next_to(self.hidden_nodes, DOWN, buff=0.4)
        out_lbl = Text("output", font_size=20, color=GRAY_B
                       ).next_to(self.output_nodes, DOWN, buff=0.4)
        self.layer_labels = VGroup(in_lbl, hid_lbl, out_lbl)

        self.play(
            *[Create(n) for n in self.input_nodes],
            *[Create(n) for n in self.hidden_nodes],
            *[Create(n) for n in self.output_nodes],
            run_time=1.2,
        )
        self.play(Create(self.edges_in_hid), Create(self.edges_hid_out),
                  run_time=1.2)
        self.play(FadeIn(self.layer_labels), run_time=0.5)
        self.wait(0.4)

    # ── Per-pattern animation ────────────────────────────────────────
    def show_pattern(self, name, inputs, firing, output_class,
                     pattern_str, subtitle=None):
        caption = Text(f"Input pattern {name}", font_size=28, color=INPUT_COLOR
                       ).to_edge(UP, buff=0.4)
        self.play(FadeIn(caption))
        if subtitle:
            sub = Text(subtitle, font_size=20, color=GRAY_B
                       ).next_to(caption, DOWN, buff=0.15)
            self.play(FadeIn(sub))
        else:
            sub = None

        # Show the input values and light up the input neurons.
        value_labels = VGroup(*[
            DecimalNumber(v, num_decimal_places=1, font_size=26, color=WHITE
                          ).next_to(self.input_nodes[i], LEFT, buff=0.25)
            for i, v in enumerate(inputs)
        ])
        self.play(FadeIn(value_labels))
        self.play(*[self._set_neuron(self.input_nodes[i], INPUT_COLOR, inputs[i])
                    for i in range(3)],
                  run_time=0.6)
        self.wait(0.3)

        # Forward pass: pulses from inputs → hidden.
        self.pulse_signals(self.input_nodes, self.hidden_nodes)

        # Hidden firing pattern.
        anims = []
        for i, fires in enumerate(firing):
            if fires:
                anims.append(self._set_neuron(self.hidden_nodes[i],
                                              FIRE_COLOR, intensity=0.85))
            else:
                anims.append(self._set_neuron(self.hidden_nodes[i],
                                              DIM_COLOR, intensity=0.0))
        self.play(*anims, run_time=0.9)

        pattern_lbl = Text(f"hidden firing pattern: {pattern_str}",
                           font_size=22, color=FIRE_COLOR
                           ).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(pattern_lbl))
        self.wait(0.8)

        # Forward pass: pulses from active hidden → outputs.
        self.pulse_signals(self.hidden_nodes, self.output_nodes,
                           only_active=firing)

        # Light the winning output neuron, dim the loser.
        winner = self.output_nodes[output_class]
        loser  = self.output_nodes[1 - output_class]
        self.play(
            self._set_neuron(winner, FIRE_COLOR, intensity=0.95),
            self._set_neuron(loser,  DIM_COLOR,  intensity=0.0),
            run_time=0.7,
        )
        out_lbl = Text(f"class {output_class}", font_size=22, color=FIRE_COLOR
                       ).next_to(winner, RIGHT, buff=0.3)
        self.play(FadeIn(out_lbl))
        self.wait(1.4)

        # Stash artefacts for cleanup.
        self._pattern_artifacts = VGroup(caption, value_labels,
                                         pattern_lbl, out_lbl)
        if sub:
            self._pattern_artifacts.add(sub)

    def reset_network(self):
        self.play(FadeOut(self._pattern_artifacts), run_time=0.4)
        anims = []
        for n in (*self.input_nodes, *self.hidden_nodes, *self.output_nodes):
            anims.append(n.animate.set_fill(GRAY_B, opacity=0.3
                                            ).set_stroke(GRAY_B, width=2))
        self.play(*anims, run_time=0.5)

    # ── Helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _set_neuron(node, colour, intensity):
        """Animate a node to the given colour with opacity ∝ intensity."""
        opacity = 0.3 + 0.6 * intensity
        return node.animate.set_fill(colour, opacity=opacity
                                     ).set_stroke(colour, width=2 + 2 * intensity)

    def pulse_signals(self, src_layer, dst_layer, only_active=None):
        """Send amber dots travelling from src to dst along their edges."""
        pulses, targets = [], []
        for i, ni in enumerate(src_layer):
            if only_active is not None and not only_active[i]:
                continue
            for nj in dst_layer:
                p = Dot(point=ni.get_center(), color=SIGNAL_COLOR, radius=0.06)
                pulses.append(p)
                targets.append(nj.get_center())
        if not pulses:
            return
        self.add(*pulses)
        self.play(*[p.animate.move_to(t) for p, t in zip(pulses, targets)],
                  run_time=0.7)
        self.remove(*pulses)

    # ── Closing insight ──────────────────────────────────────────────
    def show_emergence(self):
        net = VGroup(self.input_nodes, self.hidden_nodes, self.output_nodes,
                     self.edges_in_hid, self.edges_hid_out, self.layer_labels)
        self.play(net.animate.scale(0.65).to_edge(UP, buff=0.3),
                  run_time=0.9)

        line1 = Text("Different inputs → different firing patterns",
                     font_size=30, color=WHITE)
        line2 = Text("The pattern *is* the network's fingerprint",
                     font_size=24, color=GRAY_B, t2c={"*is*": FIRE_COLOR})
        line3 = Text('No single neuron "is" the answer.',
                     font_size=22, color=FIRE_COLOR)
        line4 = Text("Intelligence emerges from combinations of firings.",
                     font_size=22, color=FIRE_COLOR)

        block = VGroup(line1, line2, line3, line4
                       ).arrange(DOWN, buff=0.30).to_edge(DOWN, buff=0.5)

        self.play(FadeIn(line1, shift=UP * 0.3));  self.wait(0.7)
        self.play(FadeIn(line2, shift=UP * 0.2));  self.wait(0.7)
        self.play(FadeIn(line3, shift=UP * 0.2))
        self.play(FadeIn(line4, shift=UP * 0.2))
        self.wait(2.5)
