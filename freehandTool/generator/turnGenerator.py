'''
Copyright 2012 Lloyd Konneker

This is free software, covered by the GNU General Public License.
'''
import logging

from PyQt5.QtCore import QTime

from .utils.history import History

# Alternatives: uncomment only one
from .turnDetector.simpleTurnDetector import SimpleTurnDetector as TurnDetector
#from .turnDetector.reversalDetector import ReversalDetector as TurnDetector

logger = logging.getLogger(__name__)  # module level logger
logger.setLevel(level=logging.DEBUG)


class TurnGeneratorMixin(object):
  '''
  Mixin behaviour for freehand: generate turns from stream of positions.
  '''
  
  # Method name is capitalized because method *appears* to be a class.
  def TurnGenerator(self, initialPosition):
    '''
    Freehand send()'s PointerPosition when user moves graphics pointer.
    A Turn is a position between lines that lie on a axis (vertical or horizontal).
   
    This is agnostic of int versus real, with no loss of precision.
    Typically, in int.
    
    Qt doesn't have event.time . Fabricate it here.  X11 has event.time.
    
    close() may come before the first send() e.g if user just clicks pointer without moving it.
    '''
    # See below: history.start is position the last turn was generated, history.end is most recent position
    history = History(initialPosition)
    
    positionClock = QTime.currentTime()  # note restart returns elapsed
    positionClock.restart()
    # I also tried countPositionsSinceTurn to solve lag for cusp-like
    
    self.turnDetector = TurnDetector(initialPosition)
    
    try:
      while True:
        newPosition = (yield) # 2nd entry point of this coroutine
        positionElapsedTime = positionClock.restart()
        ##turn = self.detectTurn(history.end, newPosition)
        # !!! not assert newPosition is different from any prior position, including initialPosition
        turn = self.turnDetector.detect(newPosition, referencePosition=history.start)
        if turn is not None:
          self.lineGenerator.send((turn, positionElapsedTime))
          history.collapse(newPosition)
        else: # path is still on an axis with history.start: wait
          history.updateEnd(newPosition)
    # Not catching general exceptions, have not found a need for it.
    except GeneratorExit:
      self.flushTurnGenerator(history)
  
    
  def flushTurnGenerator(self, history):
    logger.debug("Flush")  
    if not history.isCollapsed():
      ''' Have position not sent. Send a turn at last known position. '''
      self.lineGenerator.send((history.end, 0)) # force a Turn 

