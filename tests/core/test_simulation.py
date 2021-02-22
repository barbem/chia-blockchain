import pytest
from tests.core.full_node.test_full_sync import node_height_at_least
from tests.setup_nodes import setup_full_system, test_constants, self_hostname
from src.util.ints import uint16
from tests.time_out_assert import time_out_assert
from src.types.peer_info import PeerInfo

test_constants_modified = test_constants.replace(
    **{
        "DIFFICULTY_STARTING": 2 ** 8,
        "DISCRIMINANT_SIZE_BITS": 1024,
        "SUB_EPOCH_BLOCKS": 140,
        "WEIGHT_PROOF_THRESHOLD": 2,
        "WEIGHT_PROOF_RECENT_BLOCKS": 350,
        "MAX_SUB_SLOT_BLOCKS": 50,
        "NUM_SPS_SUB_SLOT": 32,  # Must be a power of 2
        "EPOCH_BLOCKS": 280,
        "SUB_SLOT_ITERS_STARTING": 2 ** 20,
        "NUMBER_ZERO_BITS_PLOT_FILTER": 5,
    }
)


class TestSimulation:
    @pytest.fixture(scope="function")
    async def simulation(self):
        async for _ in setup_full_system(test_constants_modified):
            yield _

    @pytest.mark.asyncio
    async def test_simulation_1(self, simulation):
        node1, node2, _, _, _, _, _, _, _, server1 = simulation
        await server1.start_client(PeerInfo(self_hostname, uint16(21238)))
        # Use node2 to test node communication, since only node1 extends the chain.
        await time_out_assert(1000, node_height_at_least, True, node2, 7)

        async def has_compact(node1, node2):
            peak_height_1 = node1.full_node.blockchain.get_peak_height()
            headers_1 = await node1.full_node.blockchain.get_header_blocks_in_range(1, peak_height_1)
            peak_height_2 = node2.full_node.blockchain.get_peak_height()
            headers_2 = await node2.full_node.blockchain.get_header_blocks_in_range(1, peak_height_2)
            cc_eos = [False, False]
            icc_eos = [False, False]
            cc_sp = [False, False]
            cc_ip = [False, False]
            for index, headers in enumerate([headers_1, headers_2]):
                for header in headers:
                    for sub_slot in header.finished_sub_slots:
                        if sub_slot.proofs.challenge_chain_slot_proof.normalized_to_identity:
                            cc_eos[index] = True
                        if (
                            sub_slot.proofs.infused_challenge_chain_slot_proof is not None
                            and sub_slot.proofs.infused_challenge_chain_slot_proof.normalized_to_identity
                        ):
                            icc_eos[index] = True
                    if (
                        header.challenge_chain_sp_proof is not None
                        and header.challenge_chain_sp_proof.normalized_to_identity
                    ):
                        cc_sp[index] = True
                    if header.challenge_chain_ip_proof.normalized_to_identity:
                        cc_ip[index] = True

            return (
                cc_eos == [True, True] and icc_eos == [True, True] and cc_sp == [True, True] and cc_ip == [True, True]
            )

        await time_out_assert(500, has_compact, True, node1, node2)
