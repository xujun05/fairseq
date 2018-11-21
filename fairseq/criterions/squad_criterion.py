# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the LICENSE file in
# the root directory of this source tree. An additional grant of patent rights
# can be found in the PATENTS file in the same directory.

import math
import torch.nn.functional as F

from fairseq import utils

from . import FairseqCriterion, register_criterion


@register_criterion('squad')
class SquadCriterion(FairseqCriterion):

    def __init__(self, args, task):
        super().__init__(args, task)

    def forward(self, model, sample, reduce=True):

        targets = sample['target']
        net_input = sample['net_input']

        outs = model(**net_input)

        outs = [F.log_softmax(o, dim=-1).view(-1, o.size(-1)) for o in outs]
        loss = None

        for t, o in zip(targets, outs):
            if loss is None:
                loss = F.nll_loss(o, t.view(-1), size_average=False, ignore_index=self.padding_idx, reduce=reduce)
            else:
                loss += F.nll_loss(o, t.view(-1), size_average=False, ignore_index=self.padding_idx, reduce=reduce)

        sample_size = sample['nsentences'] * len(outs)

        logging_output = {
            'loss': utils.item(loss.data) if reduce else loss.data,
            'ntokens': sample['ntokens'],
            'nsentences': sample_size,
            'sample_size': sample_size,
        }
        return loss, sample_size, logging_output, outs

    @staticmethod
    def aggregate_logging_outputs(logging_outputs):
        """Aggregate logging outputs from data parallel training."""
        loss_sum = sum(log.get('loss', 0) for log in logging_outputs)
        ntokens = sum(log.get('ntokens', 0) for log in logging_outputs)
        nsentences = sum(log.get('nsentences', 0) for log in logging_outputs)
        sample_size = sum(log.get('sample_size', 0) for log in logging_outputs)
        agg_output = {
            'loss': loss_sum / sample_size / math.log(2),
            'ntokens': ntokens,
            'nsentences': nsentences,
            'sample_size': sample_size,
        }
        return agg_output
