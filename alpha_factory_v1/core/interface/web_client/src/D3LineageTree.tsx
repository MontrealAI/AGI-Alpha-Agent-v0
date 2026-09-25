// SPDX-License-Identifier: Apache-2.0
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import SpiderChart from './SpiderChart';
import RationaleModal from './RationaleModal';
import { LogicCritic, loadExamples as loadLogicExamples } from './critics/logic';
import { FeasibilityCritic } from './critics/feas';

export interface LineageNode {
  id: number;
  parent?: number | null;
  diff?: string | null;
  pass_rate: number;
}

interface Props {
  data: LineageNode[];
}

export default function D3LineageTree({ data }: Props) {
  const ref = useRef<SVGSVGElement | null>(null);
  const [selected, setSelected] = useState<LineageNode | null>(null);
  const [open, setOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [logic, setLogic] = useState<LogicCritic | null>(null);
  const [feas, setFeas] = useState<FeasibilityCritic | null>(null);
  const [scores, setScores] = useState<{ logic: number; feas: number }>({ logic: 0, feas: 0 });

  useEffect(() => {
    loadLogicExamples().then((ex) => {
      setLogic(new LogicCritic(ex));
      setFeas(new FeasibilityCritic(ex));
    });
  }, []);

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll('*').remove();
    if (!data.length) return;

    const stratify = d3
      .stratify<LineageNode>()
      .id((d) => String(d.id))
      .parentId((d) => (d.parent ? String(d.parent) : null));

    const root = stratify(data);
    const tree = d3.tree<typeof root>().size([800, 400]);
    const nodes = tree(root);

    const g = svg.append('g').attr('transform', 'translate(40,20)');

    g.selectAll('line')
      .data(nodes.links())
      .enter()
      .append('line')
      .attr('x1', (d) => d.source.x)
      .attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x)
      .attr('y2', (d) => d.target.y)
      .attr('stroke', '#999');

    const node = g
      .selectAll('circle')
      .data(nodes.descendants())
      .enter()
      .append('circle')
      .attr('cx', (d) => d.x)
      .attr('cy', (d) => d.y)
      .attr('r', 6)
      .attr('role', 'button')
      .attr('tabindex', 0)
      .attr('aria-label', (d) => `Agent ${d.data.id}, pass rate ${d.data.pass_rate}`)
      .attr('fill', (d) => d3.interpolateBlues(d.data.pass_rate))
      .style('cursor', 'pointer')
      .on('click', (_, d) => {
        setSelected(d.data);
        setOpen(false);
      })
      .on('keydown', (event, d) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          setSelected(d.data);
          setOpen(false);
        }
      });

    node.append('title').text((d) => `pass=${d.data.pass_rate}`);
  }, [data]);

  useEffect(() => {
    if (!selected || !logic || !feas) return;
    const diff = selected.diff ?? '';
    setScores({ logic: logic.score(diff), feas: feas.score(diff) });
  }, [selected, logic, feas]);

  return (
    <div>
      <svg id="lineage-tree" ref={ref} viewBox="0 0 840 440" width={840} height={440}
        aria-label="Agent lineage tree" />
      {selected && (
        <div>
          <button type="button" onClick={() => setOpen((o) => !o)}>
            {open ? 'Hide' : 'Show'} details
          </button>
          {open && (
            <div>
              <SpiderChart
                labels={['pass', 'logic', 'feas']}
                values={[selected.pass_rate, scores.logic, scores.feas]}
              />
              <table className="critic-lattice">
                <tbody>
                  <tr>
                    <th>pass</th>
                    <td>{selected.pass_rate.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <th>logic</th>
                    <td>{scores.logic.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <th>feas</th>
                    <td>{scores.feas.toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>
              {selected.diff && (
                <pre className="diff" style={{ color: '#000', backgroundColor: '#fff' }}>
                  {selected.diff}
                </pre>
              )}
              <button type="button" onClick={() => setModalOpen(true)}>
                Learn more
              </button>
              <RationaleModal
                open={modalOpen}
                onClose={() => setModalOpen(false)}
                docUrl="/alpha_factory_v1/docs/alpha_agi_agent.md"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
