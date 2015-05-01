import numpy as np
import random

from lattice_mc import atom, jump, transitions
from collections import Counter

class Lattice:

    def __init__( self, sites, cell_lengths ):
        self.cell_lengths = cell_lengths
        self.sites = sites
        self.number_of_sites = len( self.sites )
        self.site_labels = set( [ site.label for site in self.sites ] )
        self.site_populations = Counter( [ site.label for site in self.sites ] )
        self.enforce_periodic_boundary_conditions()
        self.initialise_site_lookup_table()
        self.nn_energy = False
        self.site_energies = False
        self.jump_lookup_table = False
        for site in self.sites:
            site.p_neighbours = [ self.site_with_id( i ) for i in site.neighbours ]
        self.reset()

    def enforce_periodic_boundary_conditions( self ):
        for s in self.sites:
            for i in range(3):
                if s.r[i] < 0.0:
                    s.r[i] += self.cell_lengths[i]
                if s.r[i] > self.cell_lengths[i]:
                    s.r[i] -= self.cell_lengths[i]

    def reset( self ):
        self.time = 0.0
        for site in self.sites:
            site.time_occupied = 0.0
          
    def initialise_site_lookup_table( self ):
        self.site_lookup = {}
        for site in self.sites:
            self.site_lookup[ site.number ] = site

    def site_with_id( self, number ):
        return self.site_lookup[ number ]

    def vacant_sites( self ):
        return ( site for site in self.sites if not site.is_occupied )

    def occupied_sites( self ):
        return ( site for site in self.sites if site.is_occupied )

    def vacant_site_numbers( self ):
        return [ site.number for site in self.sites if not site.is_occupied ]

    def occupied_site_numbers( self ):
        return [ site.number for site in self.sites if site.is_occupied ]
        
    def potential_jumps( self ):
        '''return all possible nearest-neighbour jumps (from occupied to neighbouring unoccupied sites)'''
        jumps = []
        if self.number_of_occupied_sites <= self.number_of_sites / 2:
            for occupied_site in self.occupied_sites():
                unoccupied_neighbours = [ site for site in [ self.site_with_id( n ) for n in occupied_site.neighbours ] if not site.is_occupied ]
                for vacant_site in unoccupied_neighbours:
                    jumps.append( jump.Jump( occupied_site, vacant_site, self.nn_energy, self.jump_lookup_table ) )
        else:
            for vacant_site in self.vacant_sites():
                occupied_neighbours = [ site for site in [ self.site_with_id( n ) for n in vacant_site.neighbours ] if site.is_occupied ]
                for occupied_site in occupied_neighbours:
                    jumps.append( jump.Jump( occupied_site, vacant_site, self.nn_energy, self.jump_lookup_table ) )
        return jumps

    def update( self, jump ):
        atom = jump.initial_site.atom
        dr = jump.dr( self.cell_lengths )
        #print( "atom {} jumped from site {} to site {}".format( atom.number, jump.initial_site.number, jump.final_site.number ) )
        jump.final_site.occupation = atom.number
        jump.final_site.atom = atom
        jump.final_site.is_occupied = True
        jump.initial_site.occupation = 0
        jump.initial_site.atom = None
        jump.initial_site.is_occupied = False
        atom.site = jump.final_site
        atom.number_of_hops += 1
        atom.dr += dr
        atom.summed_dr2 += np.dot( dr, dr )

    def populate_sites( self, number_of_atoms ):
        assert( number_of_atoms <= self.number_of_sites )
        atoms = [ atom.Atom( initial_site = site ) for site in random.sample( self.sites, number_of_atoms ) ]
        self.number_of_occupied_sites = number_of_atoms
        return atoms

    def jump( self ):
        all_transitions = transitions.Transitions( self.potential_jumps() )
        random_jump = all_transitions.random()
        delta_t = all_transitions.time_to_jump()
        self.time += delta_t
        self.update_site_occupation_times( delta_t )
        self.update( random_jump )
        return( all_transitions.time_to_jump() )

    def update_site_occupation_times( self, delta_t ):
        for site in self.occupied_sites():
            site.time_occupied += delta_t

    def site_occupation_statistics( self ):
        occupation_stats = { label : 0.0 for label in self.site_labels }
        for site in self.sites:
            occupation_stats[ site.label ] += site.time_occupied
        for label in self.site_labels:
            occupation_stats[ label ] /= self.time
        return( occupation_stats )
     
    def set_site_energies( self, energies ):
        self.site_energies = energies
        for site_label in energies:
            for site in self.sites:
                if site.label == site_label:
                    site.energy = energies[ site_label ]

    def set_nn_energy( self, delta_E ):
        self.nn_energy = delta_E

    def site_coordination_numbers( self ):
        coordination_numbers = {}
        for site in self.sites:
            if site.label not in coordination_numbers:
                coordination_numbers[ site.label ] = len( site.neighbours )
        return coordination_numbers 

    def connected_site_pairs( self ):
        site_connections = {}
        for initial_site in self.sites:
            if initial_site.label not in site_connections:
                site_connections[ initial_site.label ] = []
            for final_site in initial_site.p_neighbours:
                if final_site.label not in site_connections[ initial_site.label ]:
                    site_connections[ initial_site.label ].append( final_site.label )
        return site_connections